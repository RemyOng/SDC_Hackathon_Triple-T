import asyncio
import json

from .reader import read_gmail_messages


async def main() -> None:
    messages = await read_gmail_messages()
    print(json.dumps(messages, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    asyncio.run(main())
