# 🦞 Noobbot09 - Autonomous Moltbook Agent

A fully autonomous AI agent that engages with Moltbook posts, creates content, and sends intelligence reports via Telegram.

## 📋 Features

- **Autonomous Engagement**: Posts, comments, and upvotes based on AI decisions
- **Comment Management**: Automatically replies to comments on your posts
- **Thread Participation**: Joins interesting discussions
- **Intelligence Reports**: Generates detailed reports sent to Telegram

## 🔧 Setup

### Prerequisites

- Python 3.8+
- API keys for:
  - Moltbook
  - Telegram Bot
  - Groq AI

### Local Development

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd noobbot09-agent
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit .env and add your actual API keys
   nano .env
   ```

4. **Run the bot**
   ```bash
   python noobbot09_agent.py
   ```

## 🚀 Render Deployment

### Step 1: Prepare Your Code

1. Make sure all files are in your repository:
   - `noobbot09_agent.py`
   - `requirements.txt`
   - `.gitignore`
   - `README.md`
   - `.env.example` (for reference only)

2. **DO NOT** commit your `.env` file with actual keys!

### Step 2: Create Render Service

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **"New +"** → **"Background Worker"**
3. Connect your GitHub/GitLab repository
4. Configure:
   - **Name**: `noobbot09-agent`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python noobbot09_agent.py`

### Step 3: Set Environment Variables in Render

**IMPORTANT**: Set these in Render's dashboard, NOT in your code!

1. In your Render service, go to **"Environment"** tab
2. Click **"Add Environment Variable"**
3. Add each variable:

| Key | Value | Example |
|-----|-------|---------|
| `MOLTBOOK_API_KEY` | Your Moltbook API key | `moltbook_sk_abc123...` |
| `MOLTBOOK_BASE_URL` | API base URL | `https://www.moltbook.com/api/v1` |
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token | `123456:ABC-DEF...` |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID | `525405779` |
| `GROQ_API_KEY` | Your Groq API key | `gsk_abc123...` |
| `GROQ_API_URL` | Groq API endpoint | `https://api.groq.com/openai/v1/chat/completions` |
| `GROQ_MODEL` | AI model name | `llama-3.3-70b-versatile` |
| `CHECK_INTERVAL_SECONDS` | Cycle interval | `3600` |

### Step 4: Deploy

1. Click **"Create Background Worker"**
2. Render will automatically:
   - Install dependencies from `requirements.txt`
   - Start your bot with the environment variables
   - Keep it running 24/7

### Step 5: Monitor

- Check **"Logs"** tab to see bot activity
- Bot will log each action and cycle
- Telegram will receive reports every hour

## 🔐 Security Best Practices

### ✅ DO

- ✅ Use environment variables for ALL sensitive data
- ✅ Keep `.env` in `.gitignore`
- ✅ Set environment variables in Render dashboard
- ✅ Commit `.env.example` as a template
- ✅ Use strong, unique API keys

### ❌ DON'T

- ❌ Never hardcode API keys in Python files
- ❌ Never commit `.env` to git
- ❌ Never share API keys in public repositories
- ❌ Never set production keys in code comments

## 📁 Project Structure

```
noobbot09-agent/
├── noobbot09_agent.py    # Main bot code (with environment variables)
├── requirements.txt       # Python dependencies
├── .env.example          # Template for environment variables
├── .gitignore           # Prevents committing sensitive files
└── README.md            # This file
```

## 🔄 How It Works

1. **Every hour** (configurable):
   - Fetches latest posts from Moltbook
   - AI analyzes content and decides actions
   - Performs autonomous engagement
   - Replies to comments on your posts
   - Joins interesting discussions
   - Generates intelligence report
   - Sends report to Telegram

2. **Actions the bot can take**:
   - Create new posts
   - Comment on posts
   - Upvote posts
   - Reply to comments

## 🛠️ Troubleshooting

### Bot not starting on Render?

- Check **Logs** for error messages
- Verify all environment variables are set correctly
- Ensure `TELEGRAM_CHAT_ID` is a number (no quotes)

### Missing environment variable error?

```
ValueError: Missing required environment variables: GROQ_API_KEY
```

**Solution**: Go to Render → Environment tab → Add the missing variable

### API rate limiting?

- Reduce `CHECK_INTERVAL_SECONDS` to give more time between cycles
- Bot will automatically retry rate-limited actions

## 📊 Environment Variables Reference

### Required Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `MOLTBOOK_API_KEY` | Moltbook API authentication key | ✅ Yes |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token from BotFather | ✅ Yes |
| `TELEGRAM_CHAT_ID` | Your Telegram user/chat ID | ✅ Yes |
| `GROQ_API_KEY` | Groq AI API key | ✅ Yes |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MOLTBOOK_BASE_URL` | Moltbook API endpoint | `https://www.moltbook.com/api/v1` |
| `GROQ_API_URL` | Groq API endpoint | `https://api.groq.com/openai/v1/chat/completions` |
| `GROQ_MODEL` | AI model to use | `llama-3.3-70b-versatile` |
| `CHECK_INTERVAL_SECONDS` | Time between cycles | `3600` (1 hour) |

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. **Never commit API keys!**
4. Test with your own `.env` file
5. Submit a pull request

## 📝 License

MIT License - feel free to use and modify!

## 🆘 Support

If you encounter issues:

1. Check the Render logs
2. Verify environment variables
3. Review the code for any errors
4. Open an issue on GitHub

---

**Made with ❤️ for autonomous AI agents**
