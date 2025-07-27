A vision toolkit

# Install
```
conda create -n perceive python=3.10 -y
conda activate perceive
```

## Utils
```
pip install openai -i https://pypi.tuna.tsinghua.edu.cn/simple

```

## Visual
```
# CPU Version
pip install torch torchvision -i https://pypi.tuna.tsinghua.edu.cn/simple

# Install ultralytics for SAM2
pip install ultralytics -i https://pypi.tuna.tsinghua.edu.cn/simple

# Install GroundingDINO
cd src/grounding_dino
pip install -e . --no-build-isolation -i https://pypi.tuna.tsinghua.edu.cn/simple

# Install Cotracker
cd src/cotracker
pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install 'imageio[ffmpeg]' -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install pyarrow -i https://pypi.tuna.tsinghua.edu.cn/simple
```