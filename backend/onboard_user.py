import asyncio
from datetime import datetime, timezone
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.gmail_connection import GmailConnection

async def onboard_user(username: str):
    async with AsyncSessionLocal() as session:
        # Get user
        stmt = select(User).where(User.username == username)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            print(f"User {username} not found")
            return
        
        # Mark onboarding completed
        user.is_onboarding_completed = True
        user.is_email_verified = True
        
        # Create or update gmail connection
        stmt_gmail = select(GmailConnection).where(GmailConnection.user_id == user.id)
        result_gmail = await session.execute(stmt_gmail)
        gmail = result_gmail.scalar_one_or_none()
        if not gmail:
            gmail = GmailConnection(
                user_id=user.id,
                gmail_email=f"{username}@gmail.com",
                encrypted_refresh_token="mocked_refresh_token_not_real",
                connected_at=datetime.now(timezone.utc),
                initial_import_done=True,
                initial_import_range="6_months",
                initial_import_from=datetime.now(timezone.utc),
                scopes=["https://www.googleapis.com/auth/gmail.readonly"]
            )
            session.add(gmail)
        else:
            gmail.initial_import_done = True
            gmail.gmail_email = f"{username}@gmail.com"
        
        await session.commit()
        print(f"User {username} successfully onboarded in DB!")

if __name__ == "__main__":
    import sys
    username = sys.argv[1] if len(sys.argv) > 1 else "test_user_875412"
    asyncio.run(onboard_user(username))
