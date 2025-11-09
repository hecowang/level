#!/usr/bin/env python3
import json
import logging
import uuid
import time
import os
from dotenv import load_dotenv

load_dotenv(override=True)

APP_ID = os.getenv("APP_ID")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
VOICE_TYPE = os.getenv("VOICE_TYPE")
CLUSTER = os.getenv("CLUSTER")
ENCODING = os.getenv("ENCODING")
ENDPOINT = os.getenv("ENDPOINT")

import websockets

from app.services.tts.volcengine.protocols import MsgType, full_client_request, receive_message

logger = logging.getLogger(__name__)


def get_cluster(voice: str) -> str:
    if voice.startswith("S_"):
        return "volcano_icl"
    return "volcano_tts"


async def do_tts(text: str) -> bytes:
    # 连接并请求火山引擎 TTS 服务，根据输入文本生成语音并返回音频二进制数据

    # Connect to server
    headers = {
        "Authorization": f"Bearer;{ACCESS_TOKEN}",
    }

    logger.info(f"Connecting to {ENDPOINT} with headers: {headers}")
    websocket = await websockets.connect(
        ENDPOINT, additional_headers=headers, max_size=10 * 1024 * 1024
    )
    logger.info(
        f"Connected to WebSocket server, Logid: {websocket.response.headers['x-tt-logid']}",
    )

    try:
        # Prepare request payload
        request = {
            "app": {
                "appid": APP_ID,
                "token": ACCESS_TOKEN,
                "cluster": CLUSTER,
            },
            "user": {
                "uid": str(uuid.uuid4()),
            },
            "audio": {
                "voice_type": VOICE_TYPE,
                "encoding": ENCODING,
            },
            "request": {
                "reqid": str(uuid.uuid4()),
                "text": text,
                "operation": "submit",
                "with_timestamp": "1",
                "extra_param": json.dumps(
                    {
                        "disable_markdown_filter": False,
                    }
                ),
            },
        }

        logger.info(f"Sending TTS request: {request}")
        # Send request
        start_time = time.time()
        end_time = 0
        await full_client_request(websocket, json.dumps(request).encode())

        logger.info(f"TTS request sent")

        # Receive audio data
        audio_data = bytearray()
        while True:
            msg = await receive_message(websocket)
            if msg.type == MsgType.FrontEndResultServer:
                continue
            elif msg.type == MsgType.AudioOnlyServer:
                if end_time == 0:
                    end_time = time.time()
                    logger.info(f"[METRIC] metric=tts_first_token, value={end_time - start_time:.2f}")
                yield msg.payload
                if msg.sequence < 0:  # Last message
                    break
            else:
                raise RuntimeError(f"TTS conversion failed: {msg}")

        # Check if we received any audio data
        if not audio_data:
            raise RuntimeError("No audio data received")
    finally:
        await websocket.close()
        logger.info("Connection closed")

