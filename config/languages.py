from __future__ import annotations

LANGUAGE_LABELS = {
    "English": "English",
    "Assamese": "Assamese (অসমীয়া)",
    "Bengali": "Bengali (বাংলা)",
    "Bodo": "Bodo (बड़ो)",
    "Dogri": "Dogri (डोगरी)",
    "Gujarati": "Gujarati (ગુજરાતી)",
    "Hindi": "Hindi (हिन्दी)",
    "Kannada": "Kannada (ಕನ್ನಡ)",
    "Kashmiri": "Kashmiri (کٲشُر)",
    "Konkani": "Konkani (कोंकणी)",
    "Maithili": "Maithili (मैथिली)",
    "Malayalam": "Malayalam (മലയാളം)",
    "Manipuri / Meitei": "Manipuri / Meitei (মৈতৈলোন্)",
    "Marathi": "Marathi (मराठी)",
    "Nepali": "Nepali (नेपाली)",
    "Odia": "Odia (ଓଡ଼ିଆ)",
    "Punjabi": "Punjabi (ਪੰਜਾਬੀ)",
    "Sanskrit": "Sanskrit (संस्कृतम्)",
    "Santali": "Santali (ᱥᱟᱱᱛᱟᱲᱤ)",
    "Sindhi": "Sindhi (سنڌي)",
    "Tamil": "Tamil (தமிழ்)",
    "Telugu": "Telugu (తెలుగు)",
    "Urdu": "Urdu (اردو)",
    "Arabic": "Arabic (العربية)",
    "Chinese (simplified)": "Chinese, simplified (简体中文)",
    "French": "French (Français)",
    "German": "German (Deutsch)",
    "Hausa": "Hausa",
    "Japanese": "Japanese (日本語)",
    "Portuguese": "Portuguese (Português)",
    "Russian": "Russian (Русский)",
    "Spanish": "Spanish (Español)",
    "Swahili": "Swahili (Kiswahili)",
    "Twi": "Twi",
}

RESPONSE_LANGUAGES = tuple(LANGUAGE_LABELS)


def format_language_option(language: str) -> str:
    return LANGUAGE_LABELS[language]
