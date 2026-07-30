from datetime import date, timedelta

from sqlalchemy import select

from crm.config import settings
from crm.database import SessionLocal
from crm.models import Lead, Stage
from crm.notifications import send_telegram

SKIP_STAGES = {Stage.cliente, Stage.sem_momento}


def followup_job() -> None:
    today = date.today()
    cutoff = today + timedelta(days=settings.followup_days_ahead)

    db = SessionLocal()
    try:
        leads = db.scalars(
            select(Lead).where(
                Lead.next_action_date <= cutoff,
                Lead.next_action_date != None,
                Lead.stage.notin_(SKIP_STAGES),
            ).order_by(Lead.next_action_date.asc())
        ).all()

        if not leads:
            print(f"[followup_job] {today} — nenhum follow-up pendente.")
            return

        lines = [f"📋 *Follow-ups pendentes — {today.strftime('%d/%m/%Y')}*\n"]

        overdue = [l for l in leads if l.next_action_date < today]
        due_today = [l for l in leads if l.next_action_date == today]
        upcoming = [l for l in leads if l.next_action_date > today]

        if overdue:
            lines.append("🔴 *Atrasados:*")
            for lead in overdue:
                delta = (today - lead.next_action_date).days
                lines.append(
                    f"• {lead.company_name} ({lead.contact_name}) — "
                    f"{lead.next_action or 'sem descrição'} "
                    f"[{delta}d atraso | {lead.stage.value}]"
                )

        if due_today:
            lines.append("\n🟡 *Para hoje:*")
            for lead in due_today:
                lines.append(
                    f"• {lead.company_name} ({lead.contact_name}) — "
                    f"{lead.next_action or 'sem descrição'} "
                    f"[{lead.stage.value}]"
                )

        if upcoming:
            lines.append("\n🟢 *Próximos:*")
            for lead in upcoming:
                lines.append(
                    f"• {lead.company_name} ({lead.contact_name}) — "
                    f"{lead.next_action or 'sem descrição'} "
                    f"[{lead.next_action_date.strftime('%d/%m')} | {lead.stage.value}]"
                )

        message = "\n".join(lines)
        print(f"[followup_job] Enviando {len(leads)} follow-up(s).")
        send_telegram(message)

    finally:
        db.close()
