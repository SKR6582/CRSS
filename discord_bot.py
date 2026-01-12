import os
import discord
from dotenv import load_dotenv
from rss_news import NewsFetcher

# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()

# Discord 봇 토큰을 환경 변수에서 가져옵니다.
# .env 파일에 DISCORD_BOT_MPSB="YOUR_BOT_TOKEN" 형식으로 토큰을 저장해야 합니다.
TOKEN = os.getenv("DISCORD_BOT_MPSB")

if not TOKEN:
    raise ValueError("DISCORD_BOT_MPSB 환경 변수가 설정되지 않았습니다. .env 파일을 확인하세요.")

# Discord 클라이언트에 필요한 인텐트를 설정합니다.
intents = discord.Intents.default()
intents.message_content = True  # 메시지 내용을 읽기 위한 권한

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    """봇이 성공적으로 로그인하면 호출됩니다."""
    print(f'{client.user}으로 성공적으로 로그인했습니다!')

@client.event
async def on_message(message):
    """사용자가 메시지를 보낼 때마다 호출됩니다."""
    # 봇 자신의 메시지는 무시합니다.
    if message.author == client.user:
        return

    # '!news' 명령어를 확인합니다.
    if message.content.startswith('!news'):
        await message.channel.send("최신 뉴스를 가져오는 중입니다... 잠시만 기다려주세요.")

        try:
            # NewsFetcher를 사용하여 최신 뉴스 3개를 가져옵니다.
            fetcher = NewsFetcher(limit=3, language="ko")

            # README에 있는 샘플 피드를 사용합니다.
            urls = [
                "https://www.yna.co.kr/rss/news.xml",
                "https://feeds.bbci.co.uk/news/rss.xml",
                "https://www.theverge.com/rss/index.xml"
            ]

            news_items = fetcher.fetch(urls)

            if not news_items:
                await message.channel.send("새로운 뉴스를 찾을 수 없습니다.")
                return

            # 가져온 뉴스를 서식이 지정된 메시지로 만듭니다.
            response = "📰 최신 뉴스 3개\n\n"
            for item in news_items:
                response += f"**{item.title}**\n"
                response += f"*{item.source} - {item.published_at.strftime('%Y-%m-%d %H:%M')}*\n"
                response += f"<{item.link}>\n\n"

            # 메시지가 2000자를 초과하지 않도록 합니다.
            if len(response) > 2000:
                response = response[:1997] + "..."

            await message.channel.send(response)

        except Exception as e:
            print(f"뉴스 가져오기 오류: {e}")
            await message.channel.send("뉴스를 가져오는 중에 오류가 발생했습니다.")

# 봇을 실행합니다.
client.run(TOKEN)
