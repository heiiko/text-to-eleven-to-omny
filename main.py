from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from fastapi.responses import StreamingResponse
import openai
import logging
import httpx
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Load environment variables with error handling
try:
    ELEVENLABS_FR_API_KEY = os.environ["ELEVENLABS_FR_API_KEY"]
    ELEVENLABS_NL_API_KEY = os.environ["ELEVENLABS_NL_API_KEY"]
    OMNY_API_KEY = os.environ["OMNY_API_KEY"]
    OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
except KeyError as e:
    logging.error(f"Missing environment variable: {e}")
    raise Exception(f"Critical environment variable missing: {e}")

# Initialize FastAPI
app = FastAPI()

# Define payload basemodel
class Payload(BaseModel):
    messages: str
    config: Optional[str] = "{}"
    model: Optional[str] = "gpt-4o"

# API endpoint to start audio generation and upload
@app.post("/audio-tts/stream")
async def generate_tts(payload: Payload) -> StreamingResponse:
    return StreamingResponse(call_tts_stream(payload.messages, payload.config), media_type="text/event-stream")

# API endpoint for chat completions via OpenAI
@app.post("/chat/stream")
async def chat_stream(payload: Payload) -> StreamingResponse:
    return StreamingResponse(call_openai_chat_stream(payload.messages, payload.config, payload.model), media_type="text/event-stream")

async def call_tts_stream(messages: str, config: str):
    messages = json.loads(messages)
    config = json.loads(config)

    # Retrieve article content from message history (-1 is current user prompt; -2 is last llm response)
    article_content = messages[-2]["content"]

    yield "### Generating Elevenlabs synthetic audio\n"
    yield "This may take some time, please be patient\n\n"

    response_eleven = await generate_elevenlabs_audio(article_content, config)
    if not response_eleven:
        yield "Error encountered while generating audio\n"
        return

    yield "Audio creation completed\n"
    yield "### Creating Omnystudio clip\n"

    clip_metadata = await create_omnystudio_clip(config)
    if not clip_metadata:
        yield "Error encountered while creating clip\n"
        return

    yield "Clip creation completed\n"
    yield "### Uploading audio to Omnystudio\n"
    yield "This may take some time, please be patient\n"

    if not await upload_audio_to_omnystudio(config, clip_metadata, response_eleven.content):
        yield "Error encountered while uploading audio\n"
        return

    yield "### All done!\n"

# Step 1: generate audio file via Elevenlabs TTS
async def generate_elevenlabs_audio(text: str, parameters: dict):
    try:
        # ElevenLabs is set up in two accounts (FR vs. NL). Retrieve language and set API key
        language = parameters.get('config', {}).get('eleven_language', 'nl')
        if language == 'nl':
            ELEVENLABS_API_KEY = ELEVENLABS_NL_API_KEY
        elif language == 'fr':
            ELEVENLABS_API_KEY = ELEVENLABS_FR_API_KEY
            
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{parameters['config']['eleven_voice']}",
                json={
                    "text": text,
                    "model_id": parameters.get('config', {}).get('eleven_model', 'eleven_multilingual_v2'),
                    "voice_settings": {
                        "stability": parameters.get('config', {}).get('eleven_stability', 0.5),
                        "similarity_boost": parameters.get('config', {}).get('eleven_similarity', 0.6),
                        "style": parameters.get('config', {}).get('eleven_style', 0),
                        "use_speaker_boost": parameters.get('config', {}).get('eleven_boost', False)
                    }
                },
                headers={"xi-api-key": ELEVENLABS_API_KEY},
                params={"output_format": parameters.get('config', {}).get('eleven_output', 'mp3_44100_192')}
            )
            response.raise_for_status()
            return response
    except httpx.RequestError as e:
        logging.error(f"Error generating Elevenlabs audio: {e}")
        return None

# Step 2: Create audio clip shell in Omnystudio
async def create_omnystudio_clip(parameters: dict):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.omnystudio.com/v0/programs/{parameters['config']['program']}/clips",
                json={
                    "Title": parameters.get('article', {}).get('title', 'Unknown'),
                    "Visibility": parameters.get('config', {}).get('visibility', 'Private'),
                    "PlaylistIds": [parameters['config']['playlist']]
                },
                headers={"Authorization": f"Bearer {OMNY_API_KEY}"}
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logging.error(f"Error creating Omnystudio clip: {e}")
        return None

# Step 3: Upload Elevenlabs audio file to Omnystudio and link it to the newly created clip
async def upload_audio_to_omnystudio(parameters: dict, clip_metadata: dict, audio_content: bytes):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"https://api.omnystudio.com/v0/programs/{parameters['config']['program']}/clips/{clip_metadata['Id']}/audio",
                content=audio_content,
                headers={"Authorization": f"Bearer {OMNY_API_KEY}"}
            )
            if response.status_code != 303:
                response.raise_for_status()
            return True
    except httpx.RequestError as e:
        logging.error(f"Error uploading audio to Omnystudio: {e}")
        return False

def call_openai_chat_stream(messages: str, config: str, model: str):
    messages = json.loads(messages)
    config = json.loads(config)

    # Get streaming chat completion based on message history
    response = openai.chat.completions.create(
        model=model,
        stream=True,
        temperature=config.get('config', {}).get('openai_temperature', 0.3),
        messages=messages
    )

    try:
        # Iterate through streaming responses
        for event in response:
            current_content = event.choices[0].delta.content
            yield current_content or ""
    except Exception as e:
        logging.error(f"Error (Streaming): {e}")
