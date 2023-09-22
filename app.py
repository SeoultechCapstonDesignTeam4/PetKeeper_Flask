from flask import Flask, jsonify, request

import torch.hub
import ssl
import torch
import torch.nn as nn
import torchvision.transforms as transforms
import torch.nn.functional as F
from PIL import Image

app = Flask(__name__)

# Depthwise Separable Convolution
# Depthwise Separable Convolution
class Depthwise(nn.Module):
    def __init__(self, in_channels, out_channels, stride=1):
        super().__init__()

        self.depthwise = nn.Sequential(
            nn.Conv2d(in_channels, in_channels, 3, stride=stride, padding=1, groups=in_channels, bias=False),
            nn.BatchNorm2d(in_channels),
            nn.ReLU6(),
        )

        self.pointwise = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 1, stride=1, padding=0, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU6()
        )
    
    def forward(self, x):
        x = self.depthwise(x)
        x = self.pointwise(x)
        return x
     

# Basic Conv2d
class BasicConv2d(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size, **kwargs):
        super().__init__()

        self.conv = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size, **kwargs),
            nn.BatchNorm2d(out_channels),
            nn.ReLU()
        )

    def forward(self, x):
        x = self.conv(x)
        return x
     

# MobileNetV1
class MobileNet(nn.Module):
    def __init__(self, width_multiplier, num_classes=5, init_weights=True):
        super().__init__()
        self.init_weights=init_weights
        alpha = width_multiplier

        self.conv1 = BasicConv2d(3, int(32*alpha), 3, stride=2, padding=1)
        self.conv2 = Depthwise(int(32*alpha), int(64*alpha), stride=1)
        # down sample
        self.conv3 = nn.Sequential(
            Depthwise(int(64*alpha), int(128*alpha), stride=2),
            Depthwise(int(128*alpha), int(128*alpha), stride=1)
        )
        # down sample
        self.conv4 = nn.Sequential(
            Depthwise(int(128*alpha), int(256*alpha), stride=2),
            Depthwise(int(256*alpha), int(256*alpha), stride=1)
        )
        # down sample
        self.conv5 = nn.Sequential(
            Depthwise(int(256*alpha), int(512*alpha), stride=2),
            Depthwise(int(512*alpha), int(512*alpha), stride=1),
            Depthwise(int(512*alpha), int(512*alpha), stride=1),
            Depthwise(int(512*alpha), int(512*alpha), stride=1),
            Depthwise(int(512*alpha), int(512*alpha), stride=1),
            Depthwise(int(512*alpha), int(512*alpha), stride=1),
        )
        # down sample
        self.conv6 = nn.Sequential(
            Depthwise(int(512*alpha), int(1024*alpha), stride=2)
        )
        # down sample
        self.conv7 = nn.Sequential(
            Depthwise(int(1024*alpha), int(1024*alpha), stride=2)
        )

        self.avg_pool = nn.AdaptiveAvgPool2d((1,1))
        self.linear = nn.Linear(int(1024*alpha), num_classes)

        # weights initialization
        if self.init_weights:
            self._initialize_weights()

    def forward(self, x):
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        x = self.conv4(x)
        x = self.conv5(x)
        x = self.conv6(x)
        x = self.conv7(x)
        x = self.avg_pool(x)
        x = x.view(x.size(0), -1)
        x = self.linear(x)
        return x

    # weights initialization function
    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 0.01)
                nn.init.constant_(m.bias, 0)

device = "cuda" if torch.cuda.is_available() else   "cpu"
model = MobileNet(1, 5)

state_dict = torch.load('eye.pt', map_location=device)
# 모델의 state_dict에서 linear 레이어에 해당하는 가중치와 편향을 가져옵니다.
# model_state_dict = model.state_dict()
# for key in list(state_dict.keys()):
#     if 'linear' in key:  # linear 레이어에 해당하는 키 찾기
#         new_key = key.replace('linear', 'linear')  # 현재 모델의 키로 변경
#         state_dict[new_key] = state_dict.pop(key)
# 모델에 적용
model.load_state_dict(state_dict)
model.eval()

# model.load_state_dict(torch.load('eye.pt', map_location=device))
# model.eval()
# eye_check_model = MobileNet(1,2)
# eye_check_model.load_state_dict(torch.load('eye_detection.pt', map_location=device))
# eye_check_model = eval()

# define the transformations for the image
image_transforms = transforms.Compose([
    transforms.Resize(224),
    transforms.ToTensor()
])
 

# if __name__ == "__main__":
#     device = "cuda" if torch.cuda.is_available() else "cpu"
#     model = MobileNet(1, 2)
#     model.load_state_dict(torch.load('weights.pt', map_location=device))
#     model.eval()

#     image_transforms = transforms.Compose([
#         transforms.Resize(224),
#         transforms.ToTensor(),
#     ])

    # image = Image.open('testfile.jpeg')
    # image_tensor = image_transforms(image).unsqueeze(0)

    # with torch.no_grad():
    #   output = model(image_tensor)

    # label = ['conjunctivitis', 'normal']
    # _, predicted = torch.max(output.data, 1)
    # print('Predicted:', label[predicted.item()])

    # probabilities = F.softmax(output, dim=1)
    # predicted_class = torch.argmax(probabilities, dim=1)
    # confidence = torch.max(probabilities).item() * 100
    # print(f"Confidence: {confidence:.2f}%")
def preprocess_image(image_path):
    # 이미지를 열고 RGB 형식으로 변환
    image = Image.open(image_path).convert("RGB")
    
    # 이미지 크기를 조정 (224x224로 설정)
    image = transforms.Resize((224, 224))(image)
    
    # 이미지를 텐서로 변환
    image_tensor = transforms.ToTensor()(image)
    
    # 이미지 텐서를 모델에 맞게 정규화 (예: ImageNet의 평균 및 표준 편차)
    normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    image_tensor = normalize(image_tensor)
    
    # 배치 차원을 추가하여 모델의 예상 입력 형식으로 조정
    image_tensor = image_tensor.unsqueeze(0)
    
    return image_tensor

eye_label = ['정상', '결막염', '백내장', '색소침착성 각막염', '유루증']
eye_detection_model = torch.hub.load('ultralytics/yolov5', 'custom', path='./eye_detection.pt', force_reload=True)
eye_detection_model
test_file = './정상_눈두개.jpg'

@app.route('/test', methods=['POST'])
def test():
    try:
        # image_file = request.files['image']
        img = './정상_눈두개.jpg'
        print(eye_detection_model(img))
    except Exception as e:
        return jsonify({'error':str(e)})

@app.route('/predict', methods=['POST'])
def predict():
    try:
        image_file = request.files['image']
        
        # 이미지 전처리 함수를 사용하여 이미지를 텐서로 변환
        image_tensor = preprocess_image(image_file)

        with torch.no_grad():
            output = model(image_tensor)
        
        probabilities = F.softmax(output, dim=1)
        predicted_classes = torch.argsort(probabilities, descending=True)[0].tolist()
        class_probabilities = [probabilities[0][i].item() * 100 for i in predicted_classes]

        predicted_labels = []
        for i in predicted_classes:
            if 0 <= i < len(eye_label):
                predicted_labels.append(eye_label[i])
            else:
                predicted_labels.append("Unknown")

        data = {'Predicted': predicted_labels, 'Confidence': class_probabilities}
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)})


if __name__ == '__main__':
   app.run('0.0.0.0', port=5000, debug=True)