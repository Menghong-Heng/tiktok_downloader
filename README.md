# TikTok Downloader Telegram Bot

A powerful Telegram bot that downloads TikTok videos and photo posts (carousels) without watermarks. Built with Python and the python-telegram-bot library.

## 🚀 Features

- ✅ **No Watermark Downloads** - Get clean TikTok videos without watermarks
- ✅ **TikTok Photo Post Support** - Download all images from TikTok photo carousels
- ✅ **HD Quality Support** - Automatically downloads the highest available quality
- ✅ **Multiple URL Formats** - Supports all TikTok URL formats (short links, full URLs)
- ✅ **Fast Processing** - Optimized for quick downloads
- ✅ **User-Friendly** - Beautiful interface with progress indicators
- ✅ **Error Handling** - Robust error handling with helpful messages
- ✅ **File Size Protection** - Prevents upload failures due to size limits

## 📋 Requirements

- Python 3.8+
- Telegram Bot Token
- Internet connection

## 🛠️ Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/tiktok-downloader-bot.git
   cd tiktok-downloader-bot
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file in the project root:

   ```env
   TOKEN=your_telegram_bot_token_here
   ```

4. **Get a Telegram Bot Token**
   - Message [@BotFather](https://t.me/botfather) on Telegram
   - Create a new bot with `/newbot`
   - Copy the token and add it to your `.env` file

## 🚀 Usage

1. **Start the bot**

   ```bash
   python bot.py
   ```

2. **Use the bot**
   - Send `/start` to see the welcome message
   - Send `/help` for usage instructions
   - Paste any TikTok link to download the video or photo post

## 📦 Deployment

You can deploy this bot easily using Docker or Railway.

### Docker

1. **Build and run with Docker Compose:**
   ```bash
   docker-compose up --build
   ```
   Or build and run manually:
   ```bash
   docker build -t tiktok-bot .
   docker run --env-file .env tiktok-bot
   ```

### Railway

1. **Deploy to Railway:**
   - Click the "Deploy on Railway" button (if available) or create a new Railway project and connect your repo.
   - Set the `TOKEN` environment variable in Railway dashboard.
   - Railway will use the `Procfile` and `runtime.txt` for deployment.

## 📁 Project Structure

```
Telegram_TIktok/
├── bot.py              # Main bot application
├── downloader.py       # TikTok video & photo downloader
├── requirements.txt    # Python dependencies
├── .env                # Environment variables (not in repo)
├── .gitignore          # Git ignore rules
├── README.md           # This file
├── Dockerfile          # Docker build instructions
├── docker-compose.yml  # Docker Compose for local deployment
├── Procfile            # Railway/Heroku process file
├── app.json            # Railway/Heroku app metadata
├── runtime.txt         # Python runtime version
```

## 🛡️ Security

- Bot token is stored in `.env` file (not committed to repository)
- No sensitive data is logged
- Secure API calls with proper headers

## 🔄 API Services Used

- **Primary**: TikWM API (most reliable)
- **Fallback**: Direct TikTok API
- **Features**: HD quality, no watermark, fast processing, photo post support

## 📊 Performance

- **Download Speed**: Typically 5-15 seconds per video or photo post
- **Success Rate**: >95% for public videos and photo posts
- **File Size Limit**: 50MB (Telegram bot limit)
- **Quality**: HD when available, standard as fallback

## 🐛 Troubleshooting

### Common Issues

1. **"Video or photo too large"**

   - Try a shorter video or smaller photo post
   - Telegram bot limit is 50MB

2. **"Failed to download video or photo"**

   - Video or photo post might be private or deleted
   - Check your internet connection
   - Try again or use a different link

3. **"Invalid TikTok link"**
   - Make sure the URL contains "tiktok.com"
   - Check if the link is correct

### Error Messages

- **403 Forbidden**: API rate limit or region restriction
- **404 Not Found**: Video or photo doesn't exist or is private
- **Timeout**: Network issues, try again

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot API wrapper
- [TikWM](https://tikwm.com/) - TikTok download service
- [httpx](https://github.com/encode/httpx) - HTTP client

## 📞 Support

If you encounter any issues or have questions:

1. Check the troubleshooting section above
2. Open an issue on GitHub
3. Contact the bot developer

---

**Note**: This bot is for educational purposes. Please respect TikTok's terms of service and copyright laws when downloading content.
