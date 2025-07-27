import base64
from openai import OpenAI

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
                 image_path: str, 
                 prompt: str, 
                 stream: bool = False):
        
        # for aliyun
        img_type = image_path.split('.')[-1].lower() # png, bmp, jpeg, png, webp, heic, tiff
        if img_type in ["jpe", "jpeg", "jpg"]:
            img_type = "jpeg"

        # encode image in base64
        base64_image = None
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode("utf-8")

        # invoke
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": [{"type": "text", "text": "You are a helpful assistant."}],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{img_type};base64,{base64_image}"
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                },
            ],
            stream = stream
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