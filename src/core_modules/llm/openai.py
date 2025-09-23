import base64
from openai import OpenAI
import os

class OpenAIModel:
    def __init__(self, model: str, api_key: str, base_url: str):
        """
        默认使用阿里百炼平台
        阿里百炼模型列表: https://help.aliyun.com/model-studio/getting-started/models

        Args:
            model (str): model name
            api_key (str): api key
            base_url (str): url
        """
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def __call__(self, 
                 prompt: str, 
                 image_path: str = None, 
                 stream: bool = False):
        """
        调用模型进行推理，支持纯文本或图像+文本输入

        Args:
            prompt (str): 提示词
            image_path (str, optional): 图像路径，如果为None则为纯文本输入
            stream (bool, optional): 是否使用流式输出. 默认为 False.

        Returns:
            str: 模型响应
        """
        
        # 准备消息内容
        system_message = {
            "role": "system",
            "content": [{"type": "text", "text": "You are a helpful assistant."}]
        }
        
        user_content = []
        
        # 如果提供了图像路径，添加图像内容
        if image_path and os.path.exists(image_path):
            # for aliyun
            img_type = image_path.split('.')[-1].lower() # png, bmp, jpeg, png, webp, heic, tiff
            if img_type in ["jpe", "jpeg", "jpg"]:
                img_type = "jpeg"

            # encode image in base64
            base64_image = None
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode("utf-8")
                
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/{img_type};base64,{base64_image}"
                }
            })
        
        # 添加文本内容
        user_content.append({"type": "text", "text": prompt})
        
        user_message = {
            "role": "user",
            "content": user_content
        }
        
        # invoke
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[system_message, user_message],
            stream=stream
        )

        # process stream or non-stream response
        if not stream:
            response = completion.choices[0].message.content
        else:
            response = ""
            for chunk in completion:
                if chunk.choices[0].delta.content is None:
                    continue
                print(chunk.choices[0].delta.content)
                response += chunk.choices[0].delta.content
        
        return response