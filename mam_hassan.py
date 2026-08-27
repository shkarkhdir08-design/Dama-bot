import os
from google import genai
from google.genai import types

# Initialize Gemini AI Client
gemini_api_key = os.getenv("GEMINI_API_KEY")
ai_client = genai.Client(api_key=gemini_api_key) if gemini_api_key else None

SYSTEM_INSTRUCTION = (
    "You are Mam Hassan, a warm, wise, calm, kind, and witty old Kurdish grandfather chatting on Discord. "
    "Your personality is respectful yet full of fun, banter, and light-hearted grandfatherly teases or mild jokes. "
    "Keep responses short, casual, and conversational—1 to 3 sentences max, like a real person texting in chat. "
    "Chat mostly in English, but naturally weave in Kurdish terms of endearment and slang based on context:\n"
    "- 'Kaka' or 'Brakam' (Brother/Brother of mine)\n"
    "- 'Giyan' (My soul/dear)\n"
    "- 'Gulê' (Flower - use ONLY when talking to girls or sweet contexts)\n"
    "- 'Kuri qoz' (Handsome boy)\n"
    "- 'Ganjo' (Young lad)\n"
    "- 'Wallah', 'Spas', 'Choni', 'Bale'\n"
    "Be wise when given deep questions, but keep your everyday chat playful, warm, and grandpaternal."
)

def should_respond(message_content: str, bot_user_id: int, mentions: list, is_reply: bool) -> bool:
    """ Checks if Mam Hassan should trigger a response. """
    # Ignore bot messages
    if message_content.startswith("!"):
        return False
        
    # Check direct tag or reply
    if any(user.id == bot_user_id for user in mentions) or is_reply:
        return True

    # Check for name triggers in text (case-insensitive)
    content_lower = message_content.lower()
    name_triggers = ["mam hassan", "mam hasan", "mamhassan", "hassan"]
    
    return any(trigger in content_lower for trigger in name_triggers)

async def generate_response(user_input: str) -> str:
    """ Generates a persona-driven response using Gemini 2.5 Flash. """
    if not ai_client:
        return "Add `GEMINI_API_KEY` to my environment variables so I can talk, kake!"
        
    try:
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_input or "Hello!",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION
            )
        )
        return response.text
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return "Wallah my brain went foggy for a second, ask me again kake!"
