# alpha_check.py ─ Router-list-free version

import os, math, requests, pytz
from datetime import datetime, timedelta
from telegram import Bot

### ─── Secrets (GitHub) ───
BSC_API_KEY      = os.environ["BSC_API_KEY"]
TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = int(os.environ["TELEGRAM_CHAT_ID"])
WALLET           = os.environ["WALLET"].lower()

tz  = pytz.timezone("Asia/Seoul")
bot = Bot(TELEGRAM_TOKEN)

# ─────────────────────────────── 시간 도우미
def kst_now():        return datetime.now(tz)
def today_9am():
    n = kst_now()
    base = n.replace(hour=9, minute=0, second=0, microsecond=0)
    return base if n >= base else base - timedelta(days=1)

# ─────────────────────────────── 트xn 가져오기
def fetch_alpha_txs():
    """오늘 09:00 이후 BNB 전송 + 컨트랙트 호출(input!=0x) 트xn만"""
    url = ( "https://api.bscscan.com/api"
            f"?module=account&action=txlist&address={WALLET}"
            f"&startblock=0&endblock=99999999&sort=desc&apikey={BSC_API_KEY}" )
    j = requests.get(url, timeout=10).json()
    if j.get("status") != "1":          # API 오류 또는 트xn 없음
        return []

    start = int(today_9am().timestamp())
    res   = []
    for tx in j["result"]:
        if int(tx["timeStamp"]) < start:
            break
        if int(tx["value"]) > 0 and tx["input"] != "0x" and tx["isError"] == "0":
            res.append(tx)
    return res

# ─────────────────────────────── 볼륨 → 포인트
def bnb_price():
    p = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BNBUSDT",
                     timeout=5).json()
    return float(p["price"])

def volume_points(txs):
    tot_bnb = sum(int(tx["value"]) / 1e18 for tx in txs)
    usd     = tot_bnb * bnb_price()
    pt      = 0 if usd < 2 else math.floor(math.log2(usd / 2)) + 1
    return usd, pt, pt * 2   # x2 보너스(BNB 체인)

# ─────────────────────────────── 텔레그램
def send(msg): bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)

# ─────────────────────────────── 메인
def main():
    alpha_txs = fetch_alpha_txs()

    if not alpha_txs:                              # 매수가 없다
        if kst_now().minute == 0:                  # 매 시 정각만 경고
            send("⏰ 오늘 09:00 이후 아직 Alpha 매수가 없습니다!")
        return

    # 마지막 매수 후 경과 시간
    gap = kst_now().timestamp() - int(alpha_txs[0]["timeStamp"])
    if gap < 300:                                  # 5 분 미만이면 대기
        return

    vol, pt, pt_x2 = volume_points(alpha_txs)
    send( f"✅ Alpha 매수 완료!\n\n"
          f"• 누적 볼륨: ${vol:,.2f}\n"
          f"• 예상 Volume-Point: {pt} pt\n"
          f"• x2 이벤트 시:     {pt_x2} pt" )

if __name__ == "__main__":
    main()
