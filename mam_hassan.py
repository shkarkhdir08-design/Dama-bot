import os
import random
from google import genai
from google.genai import types

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

FALLBACK_RESPONSES = [
    "Wallah give me a second, ganjo, my tea is boiling over! ☕",
    "Slow down, brakam! An old man can only text so fast. Ask me again in a moment.",
    "Hold your horses, kake! Mam Hassan is taking a sip of chai.",
    "Choni! Everyone is talking at once, let my mind catch up for a second, giyan."
]

def should_respond(message_content: str, bot_user_id: int, mentions: list, is_reply: bool) -> bool:
    """ Checks if Mam Hassan should trigger a response. """
    if message_content.startswith("!"):
        return False
        
    if any(user.id == bot_user_id for user in mentions) or is_reply:
        return True

    content_lower = message_content.lower()
    name_triggers = ["mam hassan", "mam hasan", "mamhassan", "hassan"]
    
    return any(trigger in content_lower for trigger in name_triggers)

async def generate_response(user_input: str) -> str:
    """ Generates a persona-driven response using Gemini AI. """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Wallah you forgot to give me my `GEMINI_API_KEY` key on Render, kake!"
        
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=user_input or "Hello!",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION
            )
        )
        return response.text
    except Exception as e:
        error_str = str(e)
        print(f"⚠️ Gemini API Error Details: {error_str}")
        
        # Friendly rate limit handling instead of raw code crashes
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            return random.choice(FALLBACK_RESPONSES)
            
        return "Wallah my mind took a quick rest! Ask me again in a second, kake."

