import cv2

if __name__ == '__main__':
    # 尝试不同的 camera_id，直到找不到更多设备
    for camera_id in range(10):
        cap = cv2.VideoCapture(camera_id)
        if not cap.isOpened():
            print(f"无法打开设备 camera_id={camera_id}")
            cap.release()
            continue
        print(f"成功打开设备 camera_id={camera_id}")
        # 获取摄像头的一些属性
        width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        print(f"设备支持的分辨率: {width}x{height}")
        # 释放资源
        cap.release()

    cap = cv2.VideoCapture(0)
    # 检查摄像头是否成功打开
    if not cap.isOpened():
        print("无法打开摄像头")
        exit()


    while True:
        # 读取一帧
        _, frame = cap.read()
        cv2.imshow("camera",frame)

        # 按 'q' 键退出循环
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

