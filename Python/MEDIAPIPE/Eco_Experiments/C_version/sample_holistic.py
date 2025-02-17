#!/usr/bin/env python
# -*- coding: utf-8 -*-
import copy
import argparse

import cv2 as cv
import numpy as np
import mediapipe as mp

from utils import CvFpsCalc


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--width", help='cap width', type=int, default=1920)
    parser.add_argument("--height", help='cap height', type=int, default=1080)

    parser.add_argument('--upper_body_only', action='store_true')
    parser.add_argument("--min_detection_confidence",
                        help='face mesh min_detection_confidence',
                        type=float,
                        default=0.7)
    parser.add_argument("--min_tracking_confidence",
                        help='face mesh min_tracking_confidence',
                        type=int,
                        default=0.5)

    parser.add_argument('--use_brect', action='store_true')

    args = parser.parse_args()

    return args


def main():
    # Argument parsing #################################################################
    args = get_args()

    cap_device = args.device
    cap_width = args.width
    cap_height = args.height

    upper_body_only = args.upper_body_only
    min_detection_confidence = args.min_detection_confidence
    min_tracking_confidence = args.min_tracking_confidence

    use_brect = args.use_brect

    # Camera preparation ###############################################################
    cap = cv.VideoCapture(0)  # Webcam ID
    cap.set(3,1920)
    cap.set(4,1080)

    # Model load #############################################################
    mp_holistic = mp.solutions.holistic
    holistic = mp_holistic.Holistic(
        upper_body_only=upper_body_only,
        min_detection_confidence=min_detection_confidence,
        min_tracking_confidence=min_tracking_confidence,
    )

    # FPS measurement module ########################################################
    cvFpsCalc = CvFpsCalc(buffer_len=10)

    while True:
        display_fps = cvFpsCalc.get()

        # Camera capture #####################################################
        ret, image = cap.read()
        if not ret:
            break
        image = cv.flip(image, 1)  # Mirror display
        debug_image = copy.deepcopy(image)

        # Detection implementation #############################################################
        image = cv.cvtColor(image, cv.COLOR_BGR2RGB)

        image.flags.writeable = False
        results = holistic.process(image)
        image.flags.writeable = True

        # # Face Mesh ###########################################################
        # face_landmarks = results.face_landmarks
        # if face_landmarks is not None:
        #     # Calculation of circumscribed rectangle
        #     brect = calc_bounding_rect(debug_image, face_landmarks)
        #     # Drawing
        #     debug_image = draw_face_landmarks(debug_image, face_landmarks)
        #     debug_image = draw_bounding_rect(use_brect, debug_image, brect)

        # Pose ###############################################################
        pose_landmarks = results.pose_landmarks
        if pose_landmarks is not None:
            # Calculation of circumscribed rectangle
            brect = calc_bounding_rect(debug_image, pose_landmarks)
            # Drawing
            debug_image = draw_pose_landmarks(debug_image, pose_landmarks,
                                              upper_body_only)
            debug_image = draw_bounding_rect(use_brect, debug_image, brect)

        # Hands ###############################################################
        left_hand_landmarks = results.left_hand_landmarks
        right_hand_landmarks = results.right_hand_landmarks
        # Left Hand
        if left_hand_landmarks is not None:
            # Calculation of the center of gravity of the palm
            cx, cy = calc_palm_moment(debug_image, left_hand_landmarks)
            # Calculation of circumscribed rectangle
            brect = calc_bounding_rect(debug_image, left_hand_landmarks)
            # Drawing
            debug_image = draw_hands_landmarks(debug_image, cx, cy,
                                               left_hand_landmarks,
                                               upper_body_only, 'R')
            debug_image = draw_bounding_rect(use_brect, debug_image, brect)
        # Right Hand
        if right_hand_landmarks is not None:
            # Calculation of the center of gravity of the palm
            cx, cy = calc_palm_moment(debug_image, right_hand_landmarks)
            # Calculation of circumscribed rectangle
            brect = calc_bounding_rect(debug_image, right_hand_landmarks)
            # Drawing
            debug_image = draw_hands_landmarks(debug_image, cx, cy,
                                               right_hand_landmarks,
                                               upper_body_only, 'L')
            debug_image = draw_bounding_rect(use_brect, debug_image, brect)

        cv.putText(debug_image, "FPS:" + str(display_fps), (20, 50),
                   cv.FONT_HERSHEY_SIMPLEX, 2.0, (255, 0, 0), 3, cv.LINE_AA)

        # Key processing (ESC: end) #################################################
        key = cv.waitKey(1)
        if key == 27:  # ESC
            break

        # Show #############################################################
        cv.imshow('MediaPipe Holistic Demo', debug_image)

    cap.release()
    cv.destroyAllWindows()


def calc_palm_moment(image, landmarks):
    image_width, image_height = image.shape[1], image.shape[0]

    palm_array = np.empty((0, 2), int)

    for index, landmark in enumerate(landmarks.landmark):
        landmark_x = min(int(landmark.x * image_width), image_width - 1)
        landmark_y = min(int(landmark.y * image_height), image_height - 1)

        landmark_point = [np.array((landmark_x, landmark_y))]

        if index == 0:  # 手首1
            palm_array = np.append(palm_array, landmark_point, axis=0)
        if index == 1:  # 手首2
            palm_array = np.append(palm_array, landmark_point, axis=0)
        if index == 5:  # 人差指：付け根
            palm_array = np.append(palm_array, landmark_point, axis=0)
        if index == 9:  # 中指：付け根
            palm_array = np.append(palm_array, landmark_point, axis=0)
        if index == 13:  # 薬指：付け根
            palm_array = np.append(palm_array, landmark_point, axis=0)
        if index == 17:  # 小指：付け根
            palm_array = np.append(palm_array, landmark_point, axis=0)
    M = cv.moments(palm_array)
    cx, cy = 0, 0
    if M['m00'] != 0:
        cx = int(M['m10'] / M['m00'])
        cy = int(M['m01'] / M['m00'])

    return cx, cy


def calc_bounding_rect(image, landmarks):
    image_width, image_height = image.shape[1], image.shape[0]

    landmark_array = np.empty((0, 2), int)

    for _, landmark in enumerate(landmarks.landmark):
        landmark_x = min(int(landmark.x * image_width), image_width - 1)
        landmark_y = min(int(landmark.y * image_height), image_height - 1)

        landmark_point = [np.array((landmark_x, landmark_y))]

        landmark_array = np.append(landmark_array, landmark_point, axis=0)

    x, y, w, h = cv.boundingRect(landmark_array)

    return [x, y, x + w, y + h]


def draw_hands_landmarks(image,
                         cx,
                         cy,
                         landmarks,
                         upper_body_only,
                         handedness_str='R'):
    image_width, image_height = image.shape[1], image.shape[0]

    landmark_point = []

    # Key Point
    for index, landmark in enumerate(landmarks.landmark):
        if landmark.visibility < 0 or landmark.presence < 0:
            continue

        landmark_x = min(int(landmark.x * image_width), image_width - 1)
        landmark_y = min(int(landmark.y * image_height), image_height - 1)
        landmark_z = landmark.z

        landmark_point.append((landmark_x, landmark_y))

        if index == 0:  # 手首1
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 0, 255), 2)
        if index == 1:  # 手首2
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 0, 255), 2)
        if index == 2:  # 親指：付け根
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 0, 255), 2)
        if index == 3:  # 親指：第1関節
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 0, 255), 2)
        if index == 4:  # 親指：指先
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 0, 255), 2)
            cv.circle(image, (landmark_x, landmark_y), 12, (0, 255, 0), 2)
        if index == 5:  # 人差指：付け根
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 0, 255), 2)
        if index == 6:  # 人差指：第2関節
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 0, 255), 2)
        if index == 7:  # 人差指：第1関節
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 0, 255), 2)
        if index == 8:  # 人差指：指先
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 0, 255), 2)
            cv.circle(image, (landmark_x, landmark_y), 12, (0, 255, 255), 2)
        if index == 9:  # 中指：付け根
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 0, 255), 2)
        if index == 10:  # 中指：第2関節
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 0, 255), 2)
        if index == 11:  # 中指：第1関節
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 0, 255), 2)
        if index == 12:  # 中指：指先
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 0, 255), 2)
            cv.circle(image, (landmark_x, landmark_y), 12, (0, 255, 255), 2)
        if index == 13:  # 薬指：付け根
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 0, 255), 2)
        if index == 14:  # 薬指：第2関節
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 0, 255), 2)
        if index == 15:  # 薬指：第1関節
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 0, 255), 2)
        if index == 16:  # 薬指：指先
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 0, 255), 2)
            cv.circle(image, (landmark_x, landmark_y), 12, (0, 255, 255), 2)
        if index == 17:  # 小指：付け根
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 0, 255), 2)
        if index == 18:  # 小指：第2関節
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 0, 255), 2)
        if index == 19:  # 小指：第1関節
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 0, 255), 2)
        if index == 20:  # 小指：指先
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 0, 255), 2)
            cv.circle(image, (landmark_x, landmark_y), 12, (0, 255, 255), 2)

        if not upper_body_only:
            cv.putText(image, "z:" + str(round(landmark_z, 3)),
                       (landmark_x - 10, landmark_y - 10),
                       cv.FONT_HERSHEY_SIMPLEX, 0.25, (255, 0, 0), 1,
                       cv.LINE_AA)

    # 接続線
    if len(landmark_point) > 0:
        # 親指
        cv.line(image, landmark_point[2], landmark_point[3], (255, 0, 0), 2)
        cv.line(image, landmark_point[3], landmark_point[4], (255, 0, 0), 2)

        # 人差指
        cv.line(image, landmark_point[5], landmark_point[6], (255, 0, 0), 2)
        cv.line(image, landmark_point[6], landmark_point[7], (255, 0, 0), 2)
        cv.line(image, landmark_point[7], landmark_point[8], (255, 0, 0), 2)

        # 中指
        cv.line(image, landmark_point[9], landmark_point[10], (255, 0, 0), 2)
        cv.line(image, landmark_point[10], landmark_point[11], (255, 0, 0), 2)
        cv.line(image, landmark_point[11], landmark_point[12], (255, 0, 0), 2)

        # 薬指
        cv.line(image, landmark_point[13], landmark_point[14], (255, 0, 0), 2)
        cv.line(image, landmark_point[14], landmark_point[15], (255, 0, 0), 2)
        cv.line(image, landmark_point[15], landmark_point[16], (255, 0, 0), 2)

        # 小指
        cv.line(image, landmark_point[17], landmark_point[18], (255, 0, 0), 2)
        cv.line(image, landmark_point[18], landmark_point[19], (255, 0, 0), 2)
        cv.line(image, landmark_point[19], landmark_point[20], (255, 0, 0), 2)

        # 手の平
        cv.line(image, landmark_point[0], landmark_point[1], (255, 0, 0), 2)
        cv.line(image, landmark_point[1], landmark_point[2], (255, 0, 0), 2)
        cv.line(image, landmark_point[2], landmark_point[5], (255, 0, 0), 2)
        cv.line(image, landmark_point[5], landmark_point[9], (255, 0, 0), 2)
        cv.line(image, landmark_point[9], landmark_point[13], (255, 0, 0), 2)
        cv.line(image, landmark_point[13], landmark_point[17], (255, 0, 0), 2)
        cv.line(image, landmark_point[17], landmark_point[0], (255, 0, 0), 2)

    # 重心 + 左右
    if len(landmark_point) > 0:
        cv.circle(image, (cx, cy), 12, (255, 0, 0), 2)
        cv.putText(image, handedness_str, (cx - 6, cy + 6),
                   cv.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2, cv.LINE_AA)

    return image


# def draw_face_landmarks(image, landmarks):
#     image_width, image_height = image.shape[1], image.shape[0]
#
#     landmark_point = []
#
#     for index, landmark in enumerate(landmarks.landmark):
#         if landmark.visibility < 0 or landmark.presence < 0:
#             continue
#
#         landmark_x = min(int(landmark.x * image_width), image_width - 1)
#         landmark_y = min(int(landmark.y * image_height), image_height - 1)
#         landmark_z = landmark.z
#
#         landmark_point.append((landmark_x, landmark_y))
#
#         cv.circle(image, (landmark_x, landmark_y), 1, (0, 255, 0), 1)
#
#     if len(landmark_point) > 0:
#         # 参考：https://github.com/tensorflow/tfjs-models/blob/master/facemesh/mesh_map.jpg
#
#         # 左眉毛(55：内側、46：外側)
#         cv.line(image, landmark_point[55], landmark_point[65], (0, 255, 0), 2)
#         cv.line(image, landmark_point[65], landmark_point[52], (0, 255, 0), 2)
#         cv.line(image, landmark_point[52], landmark_point[53], (0, 255, 0), 2)
#         cv.line(image, landmark_point[53], landmark_point[46], (0, 255, 0), 2)
#
#         # 右眉毛(285：内側、276：外側)
#         cv.line(image, landmark_point[285], landmark_point[295], (0, 255, 0),
#                 2)
#         cv.line(image, landmark_point[295], landmark_point[282], (0, 255, 0),
#                 2)
#         cv.line(image, landmark_point[282], landmark_point[283], (0, 255, 0),
#                 2)
#         cv.line(image, landmark_point[283], landmark_point[276], (0, 255, 0),
#                 2)
#
#         # 左目 (133：目頭、246：目尻)
#         cv.line(image, landmark_point[133], landmark_point[173], (0, 255, 0),
#                 2)
#         cv.line(image, landmark_point[173], landmark_point[157], (0, 255, 0),
#                 2)
#         cv.line(image, landmark_point[157], landmark_point[158], (0, 255, 0),
#                 2)
#         cv.line(image, landmark_point[158], landmark_point[159], (0, 255, 0),
#                 2)
#         cv.line(image, landmark_point[159], landmark_point[160], (0, 255, 0),
#                 2)
#         cv.line(image, landmark_point[160], landmark_point[161], (0, 255, 0),
#                 2)
#         cv.line(image, landmark_point[161], landmark_point[246], (0, 255, 0),
#                 2)
#
#         cv.line(image, landmark_point[246], landmark_point[163], (0, 255, 0),
#                 2)
#         cv.line(image, landmark_point[163], landmark_point[144], (0, 255, 0),
#                 2)
#         cv.line(image, landmark_point[144], landmark_point[145], (0, 255, 0),
#                 2)
#         cv.line(image, landmark_point[145], landmark_point[153], (0, 255, 0),
#                 2)
#         cv.line(image, landmark_point[153], landmark_point[154], (0, 255, 0),
#                 2)
#         cv.line(image, landmark_point[154], landmark_point[155], (0, 255, 0),
#                 2)
#         cv.line(image, landmark_point[155], landmark_point[133], (0, 255, 0),
#                 2)
#
#         # 右目 (362：目頭、466：目尻)
#         cv.line(image, landmark_point[362], landmark_point[398], (0, 255, 0),
#                 2)
#         cv.line(image, landmark_point[398], landmark_point[384], (0, 255, 0),
#                 2)
#         cv.line(image, landmark_point[384], landmark_point[385], (0, 255, 0),
#                 2)
#         cv.line(image, landmark_point[385], landmark_point[386], (0, 255, 0),
#                 2)
#         cv.line(image, landmark_point[386], landmark_point[387], (0, 255, 0),
#                 2)
#         cv.line(image, landmark_point[387], landmark_point[388], (0, 255, 0),
#                 2)
#         cv.line(image, landmark_point[388], landmark_point[466], (0, 255, 0),
#                 2)
#
#         cv.line(image, landmark_point[466], landmark_point[390], (0, 255, 0),
#                 2)
#         cv.line(image, landmark_point[390], landmark_point[373], (0, 255, 0),
#                 2)
#         cv.line(image, landmark_point[373], landmark_point[374], (0, 255, 0),
#                 2)
#         cv.line(image, landmark_point[374], landmark_point[380], (0, 255, 0),
#                 2)
#         cv.line(image, landmark_point[380], landmark_point[381], (0, 255, 0),
#                 2)
#         cv.line(image, landmark_point[381], landmark_point[382], (0, 255, 0),
#                 2)
#         cv.line(image, landmark_point[382], landmark_point[362], (0, 255, 0),
#                 2)
#
#         # 口 (308：右端、78：左端)
#         cv.line(image, landmark_point[308], landmark_point[415], (0, 255, 0),
#                 2)
#         cv.line(image, landmark_point[415], landmark_point[310], (0, 255, 0),
#                 2)
#         cv.line(image, landmark_point[310], landmark_point[311], (0, 255, 0),
#                 2)
#         cv.line(image, landmark_point[311], landmark_point[312], (0, 255, 0),
#                 2)
#         cv.line(image, landmark_point[312], landmark_point[13], (0, 255, 0), 2)
#         cv.line(image, landmark_point[13], landmark_point[82], (0, 255, 0), 2)
#         cv.line(image, landmark_point[82], landmark_point[81], (0, 255, 0), 2)
#         cv.line(image, landmark_point[81], landmark_point[80], (0, 255, 0), 2)
#         cv.line(image, landmark_point[80], landmark_point[191], (0, 255, 0), 2)
#         cv.line(image, landmark_point[191], landmark_point[78], (0, 255, 0), 2)
#
#         cv.line(image, landmark_point[78], landmark_point[95], (0, 255, 0), 2)
#         cv.line(image, landmark_point[95], landmark_point[88], (0, 255, 0), 2)
#         cv.line(image, landmark_point[88], landmark_point[178], (0, 255, 0), 2)
#         cv.line(image, landmark_point[178], landmark_point[87], (0, 255, 0), 2)
#         cv.line(image, landmark_point[87], landmark_point[14], (0, 255, 0), 2)
#         cv.line(image, landmark_point[14], landmark_point[317], (0, 255, 0), 2)
#         cv.line(image, landmark_point[317], landmark_point[402], (0, 255, 0),
#                 2)
#         cv.line(image, landmark_point[402], landmark_point[318], (0, 255, 0),
#                 2)
#         cv.line(image, landmark_point[318], landmark_point[324], (0, 255, 0),
#                 2)
#         cv.line(image, landmark_point[324], landmark_point[308], (0, 255, 0),
#                 2)
#
#     return image


def draw_pose_landmarks(image, landmarks, upper_body_only, visibility_th=0.5):
    image_width, image_height = image.shape[1], image.shape[0]

    landmark_point = []

    for index, landmark in enumerate(landmarks.landmark):
        landmark_x = min(int(landmark.x * image_width), image_width - 1)
        landmark_y = min(int(landmark.y * image_height), image_height - 1)
        landmark_z = landmark.z
        landmark_point.append([landmark.visibility, (landmark_x, landmark_y)])

        if landmark.visibility < visibility_th:
            continue

        # if index == 0:  # 鼻
        #     cv.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), 2)
        # if index == 1:  # 右目：目頭
        #     cv.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), 2)
        # if index == 2:  # 右目：瞳
        #     cv.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), 2)
        # if index == 3:  # 右目：目尻
        #     cv.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), 2)
        # if index == 4:  # 左目：目頭
        #     cv.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), 2)
        # if index == 5:  # 左目：瞳
        #     cv.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), 2)
        # if index == 6:  # 左目：目尻
        #     cv.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), 2)
        # if index == 7:  # 右耳
        #     cv.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), 2)
        # if index == 8:  # 左耳
        #     cv.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), 2)
        # if index == 9:  # 口：左端
        #     cv.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), 2)
        # if index == 10:  # 口：左端
        #     cv.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), 2)
        if index == 11:  # 右肩
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), 2)
        if index == 12:  # 左肩
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), 2)
        if index == 13:  # 右肘
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), 2)
        if index == 14:  # 左肘
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), 2)
        if index == 15:  # 右手首
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), 2)
        if index == 16:  # 左手首
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), 2)
        if index == 17:  # 右手1(外側端)
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), 2)
        if index == 18:  # 左手1(外側端)
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), 2)
        if index == 19:  # 右手2(先端)
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), 2)
        if index == 20:  # 左手2(先端)
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), 2)
        if index == 21:  # 右手3(内側端)
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), 2)
        if index == 22:  # 左手3(内側端)
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), 2)
        if index == 23:  # 腰(右側)
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), 2)
        # if index == 24:  # 腰(左側)
        #     cv.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), 2)
        # if index == 25:  # 右ひざ
        #     cv.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), 2)
        # if index == 26:  # 左ひざ
        #     cv.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), 2)
        # if index == 27:  # 右足首
        #     cv.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), 2)
        # if index == 28:  # 左足首
        #     cv.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), 2)
        # if index == 29:  # 右かかと
        #     cv.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), 2)
        # if index == 30:  # 左かかと
        #     cv.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), 2)
        # if index == 31:  # 右つま先
        #     cv.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), 2)
        # if index == 32:  # 左つま先
        #     cv.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), 2)

        # if not upper_body_only:
        #     cv.putText(image, "z:" + str(round(landmark_z, 3)),
        #                (landmark_x - 10, landmark_y - 10),
        #                cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1,
        #                cv.LINE_AA)

    if len(landmark_point) > 0:
        # # 右目
        # if landmark_point[1][0] > visibility_th and landmark_point[2][
        #         0] > visibility_th:
        #     cv.line(image, landmark_point[1][1], landmark_point[2][1],
        #             (0, 255, 0), 2)
        # if landmark_point[2][0] > visibility_th and landmark_point[3][
        #         0] > visibility_th:
        #     cv.line(image, landmark_point[2][1], landmark_point[3][1],
        #             (0, 255, 0), 2)
        #
        # # 左目
        # if landmark_point[4][0] > visibility_th and landmark_point[5][
        #         0] > visibility_th:
        #     cv.line(image, landmark_point[4][1], landmark_point[5][1],
        #             (0, 255, 0), 2)
        # if landmark_point[5][0] > visibility_th and landmark_point[6][
        #         0] > visibility_th:
        #     cv.line(image, landmark_point[5][1], landmark_point[6][1],
        #             (0, 255, 0), 2)
        #
        # # 口
        # if landmark_point[9][0] > visibility_th and landmark_point[10][
        #         0] > visibility_th:
        #     cv.line(image, landmark_point[9][1], landmark_point[10][1],
        #             (0, 255, 0), 2)

        # 肩
        if landmark_point[11][0] > visibility_th and landmark_point[12][
                0] > visibility_th:
            cv.line(image, landmark_point[11][1], landmark_point[12][1],
                    (0, 255, 0), 2)

        # 右腕
        if landmark_point[11][0] > visibility_th and landmark_point[13][
                0] > visibility_th:
            cv.line(image, landmark_point[11][1], landmark_point[13][1],
                    (0, 255, 0), 2)
        if landmark_point[13][0] > visibility_th and landmark_point[15][
                0] > visibility_th:
            cv.line(image, landmark_point[13][1], landmark_point[15][1],
                    (0, 255, 0), 2)

        # 左腕
        if landmark_point[12][0] > visibility_th and landmark_point[14][
                0] > visibility_th:
            cv.line(image, landmark_point[12][1], landmark_point[14][1],
                    (0, 255, 0), 2)
        if landmark_point[14][0] > visibility_th and landmark_point[16][
                0] > visibility_th:
            cv.line(image, landmark_point[14][1], landmark_point[16][1],
                    (0, 255, 0), 2)

        # 右手
        if landmark_point[15][0] > visibility_th and landmark_point[17][
                0] > visibility_th:
            cv.line(image, landmark_point[15][1], landmark_point[17][1],
                    (0, 255, 0), 2)
        if landmark_point[17][0] > visibility_th and landmark_point[19][
                0] > visibility_th:
            cv.line(image, landmark_point[17][1], landmark_point[19][1],
                    (0, 255, 0), 2)
        if landmark_point[19][0] > visibility_th and landmark_point[21][
                0] > visibility_th:
            cv.line(image, landmark_point[19][1], landmark_point[21][1],
                    (0, 255, 0), 2)
        if landmark_point[21][0] > visibility_th and landmark_point[15][
                0] > visibility_th:
            cv.line(image, landmark_point[21][1], landmark_point[15][1],
                    (0, 255, 0), 2)

        # 左手
        if landmark_point[16][0] > visibility_th and landmark_point[18][
                0] > visibility_th:
            cv.line(image, landmark_point[16][1], landmark_point[18][1],
                    (0, 255, 0), 2)
        if landmark_point[18][0] > visibility_th and landmark_point[20][
                0] > visibility_th:
            cv.line(image, landmark_point[18][1], landmark_point[20][1],
                    (0, 255, 0), 2)
        if landmark_point[20][0] > visibility_th and landmark_point[22][
                0] > visibility_th:
            cv.line(image, landmark_point[20][1], landmark_point[22][1],
                    (0, 255, 0), 2)
        if landmark_point[22][0] > visibility_th and landmark_point[16][
                0] > visibility_th:
            cv.line(image, landmark_point[22][1], landmark_point[16][1],
                    (0, 255, 0), 2)

    #     # 胴体
    #     if landmark_point[11][0] > visibility_th and landmark_point[23][
    #             0] > visibility_th:
    #         cv.line(image, landmark_point[11][1], landmark_point[23][1],
    #                 (0, 255, 0), 2)
    #     if landmark_point[12][0] > visibility_th and landmark_point[24][
    #             0] > visibility_th:
    #         cv.line(image, landmark_point[12][1], landmark_point[24][1],
    #                 (0, 255, 0), 2)
    #     if landmark_point[23][0] > visibility_th and landmark_point[24][
    #             0] > visibility_th:
    #         cv.line(image, landmark_point[23][1], landmark_point[24][1],
    #                 (0, 255, 0), 2)
    #
    #     if len(landmark_point) > 25:
    #         # 右足
    #         if landmark_point[23][0] > visibility_th and landmark_point[25][
    #                 0] > visibility_th:
    #             cv.line(image, landmark_point[23][1], landmark_point[25][1],
    #                     (0, 255, 0), 2)
    #         if landmark_point[25][0] > visibility_th and landmark_point[27][
    #                 0] > visibility_th:
    #             cv.line(image, landmark_point[25][1], landmark_point[27][1],
    #                     (0, 255, 0), 2)
    #         if landmark_point[27][0] > visibility_th and landmark_point[29][
    #                 0] > visibility_th:
    #             cv.line(image, landmark_point[27][1], landmark_point[29][1],
    #                     (0, 255, 0), 2)
    #         if landmark_point[29][0] > visibility_th and landmark_point[31][
    #                 0] > visibility_th:
    #             cv.line(image, landmark_point[29][1], landmark_point[31][1],
    #                     (0, 255, 0), 2)
    #
    #         # 左足
    #         if landmark_point[24][0] > visibility_th and landmark_point[26][
    #                 0] > visibility_th:
    #             cv.line(image, landmark_point[24][1], landmark_point[26][1],
    #                     (0, 255, 0), 2)
    #         if landmark_point[26][0] > visibility_th and landmark_point[28][
    #                 0] > visibility_th:
    #             cv.line(image, landmark_point[26][1], landmark_point[28][1],
    #                     (0, 255, 0), 2)
    #         if landmark_point[28][0] > visibility_th and landmark_point[30][
    #                 0] > visibility_th:
    #             cv.line(image, landmark_point[28][1], landmark_point[30][1],
    #                     (0, 255, 0), 2)
    #         if landmark_point[30][0] > visibility_th and landmark_point[32][
    #                 0] > visibility_th:
    #             cv.line(image, landmark_point[30][1], landmark_point[32][1],
    #                     (0, 255, 0), 2)
    return image


def draw_bounding_rect(use_brect, image, brect):
    if use_brect:
        # 外接矩形
        cv.rectangle(image, (brect[0], brect[1]), (brect[2], brect[3]),
                     (0, 255, 0), 2)

    return image


if __name__ == '__main__':
    main()
