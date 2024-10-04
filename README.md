# text-to-eleven-to-omnystudio

FastAPI server to chain ElevenLabs & OmnyStudio APIs:
- ElevenLabs TTS audio file generation
- OmnyStudio clip generation & audio hosting

## Quickstart

Set your API keys (OPENAI, ELEVENLABS_API_KEY & OMNY_API_KEY)

Install requirements
```bash
$ pip install -r requirements.txt
```

Run the server
```bash
$ uvicorn main:app
```
Note - if you put it behind a nginx (or whatever) make sure to allow for streaming responses

## Request parameters

- LLM message history
- ElevenLabs
  - Voice ID (_eleven_voice_, required)
  - Model ID (_eleven_model_, optional)
  - Voice stability (_eleven_stability_, optional)
  - Voice similarity (_eleven_similarity_, optional)
  - Voice style exaggeration (_eleven_style_, optional)
  - Voice speaker boost (_eleven_boost_, optional)
  - Audio output format (_eleven_output_, optional)
- OmnyStudio
  - Destination program (_omny_program_, required)
  - Dastination playlist (_omny_playlist_, required)
  - Created clip visibility (_omny_visibility_, optional)
- Content metadata
  - Content title (_article_title_, optional)

## Example

POST request to /audio-tts/stream

```javascript
var messages = messages=[
  {
    "role": "user",
    "content": [{
      "type": "text",
      "text": "Transform your last output to audio via TTS"
    }]
  },
  {
    "role": "assistant",
    "content": [{
      "type": "text",
      "text": "<TTS TEXT GOES HERE>"
    }]
  }
];
var settings = {
    'config': {
        'eleven_voice': '<Elevenlabs Voice ID>',
        'omny_playlist': '<OmnyStudio Playlist ID>',
        'omny_program': '<OmnyStudio Program ID>'
    },
    'metadata': {
        'article_title': '<Content title>'
    }
};
settings = JSON.stringify(settings);

fetch('http://localhost:8080/audio-tts/stream', {
    method: "POST",
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({"messages": messages, "config": settings}),
});
```
