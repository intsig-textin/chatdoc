

from app.support.helper import log_duration
from config.config import settings, LlmSettings
from app.libs.llm import QWenChat, DeepSeekChat, GptTurbo
import logging


class LLM:

    def __init__(self):
        self._model = settings.llm.llm
        self._model_config = getattr(settings.llm, self._model)

    @log_duration()
    def chat(self, system_message, prompt, stream):
        logging.info(f"llm_model: {self._model}, model: {self._model_config.model}, prompt len: {len(prompt)}")
        if self._model == "qwen":
            self._model_config: LlmSettings.Qwen
            gen_conf = dict(
                max_tokens=self._model_config.max_token,
                top_p=self._model_config.top_p,
                temperature=self._model_config.temperature,
                presence_penalty=self._model_config.presence_penalty,
                enable_search=self._model_config.enable_search
            )
            chat = QWenChat(key=self._model_config.api_key, model_name=self._model_config.model)

        elif self._model == "deepseek":
            self._model_config: LlmSettings.Deepseek
            gen_conf = dict(
                max_tokens=self._model_config.max_token,
                top_p=self._model_config.top_p,
                temperature=self._model_config.temperature,
                presence_penalty=self._model_config.presence_penalty,
            )
            chat = DeepSeekChat(key=self._model_config.api_key, model_name=self._model_config.model, base_url=self._model_config.url)

        else:
            self._model = "gpt"
            self._model_config: LlmSettings.Gpt = settings.llm.gpt
            gen_conf = dict(
                max_tokens=self._model_config.max_token,
                top_p=self._model_config.top_p,
                temperature=self._model_config.temperature,
                presence_penalty=self._model_config.presence_penalty,
            )
            chat = GptTurbo(key=self._model_config.api_key, model_name=self._model_config.model, base_url=self._model_config.url)

        history = [{"role": "user", "content": prompt}]
        if stream:
            return chat.chat_streamly(system=system_message, history=history, gen_conf=gen_conf)
        else:
            return chat.chat(system=system_message, history=history, gen_conf=gen_conf)
