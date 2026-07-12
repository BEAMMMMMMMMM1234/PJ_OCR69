from __future__ import annotations

import json
import os
import time
from typing import Any
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = PROJECT_ROOT / "prompts"
GEMMA_DEBUG_DIR = PROJECT_ROOT / "runtime" / "debug" / "gemma"


class GemmaPostProcessor:
    def __init__(
        self,
        use_gemma: bool | None = None,
        model: str | None = None,
        timeout_seconds: int = 30,
        ollama_host: str | None = None,
    ) -> None:
        if use_gemma is None:
            use_gemma = os.getenv("USE_GEMMA", "false").strip().lower() == "true"
        self.use_gemma = use_gemma
        self.model = model or os.getenv("GEMMA_MODEL", "gemma4:latest")
        self.timeout_seconds = timeout_seconds
        self.ollama_host = (ollama_host or os.getenv("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")

    def postprocess(
        self,
        document_type: str,
        validated_data: dict[str, Any],
        raw_text: str | None = None,
        debug_name: str | None = None,
    ) -> dict[str, Any]:
        fallback_data = dict(validated_data or {})
        prompt, prompt_path = self._build_prompt(document_type, fallback_data, raw_text or "")
        started_at = time.perf_counter()
        if not self.use_gemma:
            debug_payload = self._build_debug_payload(
                document_type=document_type,
                prompt_path=prompt_path,
                prompt=prompt,
                response_text="",
                response_json=None,
                approval=False,
                used=False,
                error=None,
                fallback_data=fallback_data,
                cleaned_data=fallback_data,
                started_at=started_at,
                endpoint=None,
            )
            self._write_debug_artifact(debug_name, debug_payload)
            return {
                "data": fallback_data,
                "attempted": False,
                "used": False,
                "success": False,
                "approval": False,
                "error": None,
                "debug": debug_payload,
            }

        generate_error: str | None = None
        response_text = ""
        response_json: dict[str, Any] | None = None
        used_endpoint: str | None = None
        for endpoint, payload_builder in (
            ("generate", self._build_generate_payload),
            ("chat", self._build_chat_payload),
        ):
            try:
                response = requests.post(
                    f"{self.ollama_host}/api/{endpoint}",
                    json=payload_builder(prompt),
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                response_json = response.json()
                response_text = self._extract_response_text(endpoint, response_json)
                cleaned_data = self._parse_json_response(response_text)
                if not isinstance(cleaned_data, dict):
                    raise ValueError("Gemma response is not a JSON object")
                used_endpoint = endpoint
                debug_payload = self._build_debug_payload(
                    document_type=document_type,
                    prompt_path=prompt_path,
                    prompt=prompt,
                    response_text=response_text,
                    response_json=response_json,
                    approval=True,
                    used=True,
                    error=None,
                    fallback_data=fallback_data,
                    cleaned_data=cleaned_data or fallback_data,
                    started_at=started_at,
                    endpoint=endpoint,
                )
                self._write_debug_artifact(debug_name, debug_payload)
                return {
                    "data": cleaned_data or fallback_data,
                    "attempted": True,
                    "used": True,
                    "success": True,
                    "approval": True,
                    "error": None,
                    "debug": debug_payload,
                }
            except Exception as exc:  # noqa: BLE001
                generate_error = str(exc)
                response_text = response_text or ""
                continue

        debug_payload = self._build_debug_payload(
            document_type=document_type,
            prompt_path=prompt_path,
            prompt=prompt,
            response_text=response_text,
            response_json=response_json,
            approval=False,
            used=False,
            error=generate_error,
            fallback_data=fallback_data,
            cleaned_data=fallback_data,
            started_at=started_at,
            endpoint=used_endpoint,
        )
        self._write_debug_artifact(debug_name, debug_payload)
        return {
            "data": fallback_data,
            "attempted": True,
            "used": False,
            "success": False,
            "approval": False,
            "error": generate_error,
            "debug": debug_payload,
        }

    def _build_prompt(
        self,
        document_type: str,
        validated_data: dict[str, Any],
        raw_text: str,
    ) -> tuple[str, str]:
        template = self._load_prompt_template(document_type)
        schema_hint = json.dumps(validated_data, ensure_ascii=False, indent=2)
        return (
            template.format(
                document_type=document_type,
                validated_data=schema_hint,
                raw_text=raw_text,
            ),
            str(self._prompt_path(document_type).relative_to(PROJECT_ROOT)),
        )

    def _load_prompt_template(self, document_type: str) -> str:
        prompt_path = self._prompt_path(document_type)
        if prompt_path and prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
        return (
            "You are an OCR JSON approval layer.\n"
            "Fix only obvious OCR typos.\n"
            "Do not invent new facts.\n"
            "Do not add fields outside the approved schema.\n"
            "If there is no evidence in OCR, keep \"ไม่พบ\".\n"
            "Return JSON only.\n\n"
            "document_type: {document_type}\n"
            "validated_data:\n{validated_data}\n"
            "raw_text:\n{raw_text}\n"
        )

    def _build_generate_payload(self, prompt: str) -> dict[str, Any]:
        return {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }

    def _build_chat_payload(self, prompt: str) -> dict[str, Any]:
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Return JSON only. Do not invent facts."},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        }

    def _extract_response_text(self, endpoint: str, payload: dict[str, Any]) -> str:
        if endpoint == "generate":
            return str(payload.get("response", "") or "")
        if endpoint == "chat":
            message = payload.get("message", {}) or {}
            if isinstance(message, dict):
                return str(message.get("content", "") or "")
            return ""
        return ""

    def _parse_json_response(self, response_text: str) -> dict[str, Any] | None:
        text = (response_text or "").strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except Exception:
            pass

        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except Exception:
                return None
        return None

    def _build_debug_payload(
        self,
        document_type: str,
        prompt_path: str,
        prompt: str,
        response_text: str,
        response_json: dict[str, Any] | None,
        approval: bool,
        used: bool,
        error: str | None,
        fallback_data: dict[str, Any],
        cleaned_data: dict[str, Any],
        started_at: float,
        endpoint: str | None,
    ) -> dict[str, Any]:
        latency_seconds = round(time.perf_counter() - started_at, 4)
        latency_ms = round(latency_seconds * 1000.0, 2)
        changed_fields = self._diff_fields(fallback_data, cleaned_data)
        return {
            "artifact_type": "gemma_debug",
            "document_type": document_type,
            "model": self.model,
            "prompt_path": prompt_path,
            "endpoint": endpoint,
            "approval": approval,
            "used": used,
            "latency_seconds": latency_seconds,
            "latency_ms": latency_ms,
            "prompt": prompt,
            "response_text": response_text,
            "response_json": response_json,
            "changed_fields": changed_fields,
            "warnings": [] if approval else ([error] if error else []),
            "error": error,
        }

    def _diff_fields(self, before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
        changed: list[dict[str, Any]] = []
        keys = sorted(set(before.keys()) | set(after.keys()))
        for key in keys:
            before_value = before.get(key)
            after_value = after.get(key)
            if before_value != after_value:
                changed.append(
                    {
                        "field": key,
                        "before": before_value,
                        "after": after_value,
                    }
                )
        return changed

    def _write_debug_artifact(self, debug_name: str | None, payload: dict[str, Any]) -> None:
        if not debug_name:
            return
        GEMMA_DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        artifact_path = GEMMA_DEBUG_DIR / f"{debug_name}_gemma.json"
        artifact_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _prompt_path(self, document_type: str) -> Path:
        prompt_map = {
            "Appointment": PROMPTS_DIR / "appointment_prompt.txt",
            "MedicineLabel": PROMPTS_DIR / "medicine_prompt.txt",
        }
        return prompt_map.get(document_type, PROMPTS_DIR / "generic_prompt.txt")
