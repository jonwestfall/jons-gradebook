from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.encryption import decrypt_text, encrypt_text
from app.db.models import LLMOutput, LLMProvider, LLMRun, LLMRunStatus
from app.services.llm.deidentify import DeidentifyService
from app.services.llm.providers import provider_factory


def create_preview_run(db: Session, provider: LLMProvider, model: str, prompt: str) -> LLMRun:
    deidentify = DeidentifyService(db)
    result = deidentify.apply(prompt)

    run = LLMRun(
        provider=provider,
        model=model,
        input_text_encrypted=encrypt_text(prompt),
        deidentified_preview=result.preview_text,
        deidentify_map=result.replacements,
        status=LLMRunStatus.previewed,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def send_run(db: Session, run_id: int) -> LLMOutput:
    run = db.get(LLMRun, run_id)
    if not run:
        raise ValueError("Run not found")

    if run.status not in {LLMRunStatus.previewed, LLMRunStatus.failed}:
        raise ValueError("Run must be previewed before send")

    run.status = LLMRunStatus.sent
    run.sent_at = datetime.now(timezone.utc)
    db.commit()

    try:
        provider = provider_factory(run.provider)
        response = provider.generate(prompt=run.deidentified_preview, model=run.model)

        output = LLMOutput(run_id=run.id, output_text_encrypted=encrypt_text(response.output_text))
        run.status = LLMRunStatus.completed
        run.completed_at = datetime.now(timezone.utc)
        db.add(output)
        db.commit()
        db.refresh(output)
        return output
    except Exception as exc:
        run.status = LLMRunStatus.failed
        run.error_message = str(exc)
        db.commit()
        raise


def get_run_with_output(db: Session, run_id: int) -> dict:
    run = db.get(LLMRun, run_id)
    if not run:
        raise ValueError("Run not found")

    outputs = []
    for output in run.outputs:
        outputs.append(
            {
                "output_id": output.id,
                "output_text": decrypt_text(output.output_text_encrypted),
                "edited_text": decrypt_text(output.edited_text_encrypted) if output.edited_text_encrypted else None,
            }
        )

    return {
        "id": run.id,
        "provider": run.provider.value,
        "model": run.model,
        "status": run.status.value,
        "preview": run.deidentified_preview,
        "deidentify_map": run.deidentify_map,
        "error_message": run.error_message,
        "outputs": outputs,
    }


def update_output_text(db: Session, output_id: int, edited_text: str) -> LLMOutput:
    output = db.get(LLMOutput, output_id)
    if not output:
        raise ValueError("Output not found")

    output.edited_text_encrypted = encrypt_text(edited_text)
    db.commit()
    db.refresh(output)
    return output
