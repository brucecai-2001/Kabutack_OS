from src.visual.vlm.api import OpenAIModel

if __name__ == "__main__":
    model = OpenAIModel(model="qwen2.5-vl-32b-instruct", api_key="sk-ba730a7d81fe4cdbbe9729dcda4e1e88", base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
    res = model(image_path="src/visual/grounding_dino/.asset/cat_dog.jpeg", prompt="how many cats are there", stream=True)
    print(res)