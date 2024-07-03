# text-to-eleven-to-omnystudio

FastAPI server to automate and chain
* TTS audio generation (via Elevenlabs)
* Audio hosting (via OmnyStudio) 

## Quickstart

Set your API keys (ELEVENLABS_API_KEY & OMNY_API_KEY)

Install requirements
```bash
$ pip install -r requirements.txt
```

Run the server
```bash
$ uvicorn main:app
```

Now do a POST request to /audio-tts/stream

## Example

```javascript
var text = "<TTS text sample goes here>";
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
    body: JSON.stringify({"content": text, "config": settings}),
})
```
