# Telegram Quiz Bot 🤖

A bot that converts text files into interactive Telegram quizzes with admin features

## Features ✨
- Parses .txt files with quiz questions
- Validates question format
- Sends quizzes as interactive 10-second polls
- Detailed error reporting
- **Admin Statistics** (`/stats`)
- **User Broadcasting** (`/broadcast`)
- Health monitoring dashboard
- MongoDB user tracking

## Setup Instructions ⚙️

### 1. Prerequisites
- Python 3.9+
- MongoDB database ([free tier](https://www.mongodb.com/atlas/database))
- Telegram account with [@BotFather](https://t.me/BotFather)

### 2. Get Credentials
```bash
# Get your Telegram user ID
1. Start conversation with @userinfobot on Telegram
2. Send any message → You'll receive your user ID

# Get bot token
1. Create new bot with @BotFather → /newbot
2. Copy API token
