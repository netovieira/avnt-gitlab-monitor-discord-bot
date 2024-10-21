from datetime import datetime
import pytz
from dateutil.relativedelta import relativedelta

def format_date(date_string, forHuman=False):
    if not date_string:
        return "N/A"
    date = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
    sao_paulo_tz = pytz.timezone("America/Sao_Paulo")
    date = date.astimezone(sao_paulo_tz)
    formatted_date = date.strftime("%d/%m/%Y às %H:%M:%S")
    
    now = datetime.now(pytz.utc)
    diff = relativedelta(now, date)
    
    if diff.years > 0:
        if diff.years == 1:
            humanized = "Um ano atrás"
        else:
            humanized = f"{diff.years} anos atrás"
    elif diff.months > 0:
        if diff.months == 1:
            humanized = "Um mês atrás"
        else:
            humanized = f"{diff.months} meses atrás"
    elif diff.days > 0:
        if diff.days == 1:
            humanized = "Um dia atrás"
        else:
            humanized = f"{diff.days} dias atrás"
    elif diff.hours > 0:
        if diff.hours == 1:
            humanized = "Uma hora atrás"
        else:
            humanized = f"{diff.hours} horas atrás"
    elif diff.minutes > 0:
        if diff.minutes == 1:
            humanized = "Um minuto atrás"
        else:
            humanized = f"{diff.minutes} minutos atrás"
    else:
        if diff.seconds == 1:
            humanized = "Um segundo atrás"
        else:
            humanized = f"{diff.seconds} segundos atrás"
    
    if forHuman:
        return f"{humanized}"
    
    return f"{formatted_date}"