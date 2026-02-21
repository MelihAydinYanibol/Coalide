# Coalide - Interactive Quiz Learning Application

<div align="center">

**A Python-based interactive quiz application with Telegram integration, text-to-speech support, and parental controls.**

</div>

---

## Future Features
- [ ] Integration with parental controls
- [ ] Multi-Language Support
- [ ] Startup admin interface (press - on startup) UI and menu itself
- [ ] More commmands in admin controls (pos command for selecting an key with its abs position)
- [ ] Admin Controls (on setup) will have detailed statistics and can control/manipulate stats. Admin controls will also have a way to reset statistic for test purposes
- [ ] Optimization
- [ ] POTENTIAL : Admin Console with TUI with dropback to legacy

## 🎯 Overview

Coalide is an interactive quiz application designed to make learning engaging and fun. It features:

- **Multi-level Quiz System**: Multiple difficulty levels with customizable question counts
- **Text-to-Speech Support**: Pronunciation assistance using gTTS (Google Text-to-Speech)
- **Telegram Integration**: Real-time learning progress reports sent to Telegram
- **Parental Controls**: Integration with parental control systems for managing app usage exceptions
- **ASCII Art UI**: Beautiful ASCII animations and menus for enhanced user experience
- **Statistics Tracking**: Detailed analytics and performance tracking
- **Admin Console**: Management interface for system administration

---

## 🚀 Features

### Core Features

- **Interactive Quiz Mode**: Original quiz mode with multiple levels
- **Dummy Mode**: Practice mode
- **Speech Synthesis**: Text-to-speech pronunciation for vocabulary learning
- **Progress Tracking**: Detailed statistics and analytics stored locally
- **Telegram Notifications**: Automatic quiz result reporting via Telegram

### Admin Features

- **Admin Console**: Terminal User Interface (TUI) for administrative tasks
- **Configuration Management**: Easy configuration through `config.json`
- **Debug Mode**: Built-in debug logging for development

### Parental Features

- **Exception Management**: Integration with parental control system to add time exceptions for applications
- **Custom Reasons**: Support for logging reasons for time exceptions
- **Date-based Tracking**: Per-date exception tracking

---

## 📋 Requirements

### Python Packages

See `requirements.txt` for complete dependencies. Key packages include:

- **User Interface**: `asciimatics`, `colorama`, `pyfiglet`
- **Audio**: `PyAudio`, `pydub`, `gTTS`
- **Web/API**: `requests`, `httpx`
- **Data Processing**: `numpy`, `pillow`, `mutagen`
- **I/O**: `python-dotenv`, `inputimeout`

### System Requirements

- Python 3.12.x
- Windows (uses `pywin32` for Windows-specific features)
- Optional: Telegram Bot token for notifications

---

## 🔧 Installation

### 1. Clone and Setup

```bash
cd c:\Users\melih\Desktop\Projects\Coalide
```

### 2. Create Virtual Environment (Optional but Recommended)

The project includes a pre-configured `env/` virtual environment.

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create or modify `.env` file:

```env
ADMIN_PASSWORD=0000
PARENTAL_CONTROL_URL=http://device-ip:5005
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
CHAT_ID=YOUR_TELEGRAM_CHAT_ID
```

### 5. Configure Application

Edit `config.json` to customize:

```json
{
    "default_quiz_config": {
        "level_1_question_count": 20,
        "level_2_question_count": 4,
        "random_order": true,
        "pronounce_words": true,
        "send_telegram_message": true,
        "save_statistics": true
    },
    "dummy_mode": {
        "dummy_mode": true,
        "dummy_question_count": 10,
        "send_telegram_message": true,
        "pronounce_words": false
    },
    "general": {
        "spam_answer_proof": false,
        "set_time_for_pc": true,
        "set_time_for_tomorrow": true,
        "answer_timeout": 15
    }
}
```

---

## 📖 Usage

### Running the Application

```bash
python main.py
```

### Debug Mode

```bash
python main.py -debug
```

This enables detailed logging for troubleshooting.

### Features

- **Interactive Quiz**: Answer questions with configurable time limits
- **Statistics**: View your learning progress and performance metrics
- **Admin Console**: Access admin features (requires password)
- **Telegram Reports**: Automatic progress reports to your Telegram account

---

## 🗂️ Project Structure

```
Coalide/
├── main.py                      # Main application entry point
├── telegram_report.py           # Telegram integration module
├── parental_connection.py       # Parental control integration
├── BETA_admin_console_test_TUI.py  # Admin console interface
├── config.json                  # Application configuration
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables
│
├── ASCII/                       # ASCII art and animations
│   ├── ASCII_start_menu.py
│   ├── ASCII_selection_menu.py
│   ├── ASCII_LevelUp.py
│   └── Animations/
│       ├── video.py
│       ├── gifs.txt
│       └── DB_VDATA.csv
│
├── Manuals/                     # Documentation
│   └── Create_daily_stats_manually.py
│
├── Data Files
│   ├── analytics.csv
│   ├── daily_stats.csv
│   ├── statistics.csv
│   ├── words.csv
│   ├── used_exceptions.csv
│   └── sent_tg_messages.json
│
└── env/                         # Python virtual environment
```

---

## 🔌 Integration Guides

### Telegram Integration

1. **Get Bot Token**:
   - Message [@BotFather](https://t.me/botfather) on Telegram
   - Create a new bot and get your `BOT_TOKEN`

2. **Get Chat ID**:
   - Message your bot to start a conversation
   - Use a service like [@userinfobot](https://t.me/userinfobot) to get your `CHAT_ID`

3. **Configure `.env`**:
   ```env
   BOT_TOKEN=your_bot_token_here
   CHAT_ID=your_chat_id_here
   ```

### Parental Controls Integration

Configure the parental control server URL in `.env`:

```env
PARENTAL_CONTROL_URL=http://your-server-ip:5005
```

The application can automatically add time exceptions to your parental control system.

---

## ⚙️ Configuration Guide

### Quiz Settings

Modify `config.json` to customize:

- **Question Count**: Set number of questions per level
- **Random Order**: Shuffle questions randomly
- **Pronunciation**: Enable/disable text-to-speech
- **Telegram Reports**: Enable/disable automatic reporting
- **Statistics Saving**: Track quiz performance

### General Settings

- **Spam Answer Proof**: Prevent rapid answer submissions
- **Answer Timeout**: Set time limit for answers (seconds)
- **PC Time Settings**: Sync with parental control system

---

## 📊 Data & Statistics

The application tracks:

- **Quiz Performance**: Accuracy, time taken, difficulty level
- **Analytics**: Overall progress trends
- **Daily Stats**: Performance metrics per day
- **Sent Messages**: Log of Telegram messages sent

---

## 🛠️ Troubleshooting

### Audio Issues

- Ensure PyAudio is properly installed
- Check Windows audio settings
- Verify microphone permissions

### Telegram Issues

- Verify `BOT_TOKEN` and `CHAT_ID` are correct
- Check internet connection
- Ensure bot has message permissions

### Parental Control Connection

- Parental Control refers to my other repo (cekirge1972/PCV2)
- Verify `PARENTAL_CONTROL_URL` is correct
- Check if parental control server is running
- Ensure proper network connectivity

### Debug Mode

Run with debug flag for detailed logs:

```bash
python main.py -debug
```

---

## 📝 API Reference

### Core Functions

**`get_config(keys=None)`**
- Retrieves application configuration
- Parameters: Optional list of config keys
- Returns: Configuration dictionary

**`lg()`**
- Debug logging function
- Prints messages only in debug mode
- Enabled with `-debug` flag

**`cls()`**
- Clears screen
- Platform-independent implementation

### Telegram Module

**`send_telegram_report(report_message, ...)`**
- Sends quiz results to Telegram
- Supports formatted messages
- Configurable via environment variables

### Parental Control Module

**`add_exceptional_time(base_url, app_name, duration_seconds, ...)`**
- Adds time exception for specified application
- Parameters:
  - `base_url`: Parental control server URL
  - `app_name`: Application executable name
  - `duration_seconds`: Additional time in seconds
  - `exception_date`: Optional date (YYYY-MM-DD)
  - `reason`: Reason for exception

---

## 🤝 Contributing

Submit pull requests or report issues for improvements and bug fixes.

---

## 📄 License

This project is part of the Coalide learning system.

---

## 📞 Support

For issues or questions:

1. Check the `Manuals/` folder for detailed guides
2. Enable debug mode for troubleshooting
3. Review `config.json` for configuration issues
4. Check environment variables in `.env`

---

**Last Updated**: February 2026
