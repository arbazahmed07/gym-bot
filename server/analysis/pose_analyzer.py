import cv2
import mediapipe as mp
import numpy as np
import json
import sys
import math
import os
import warnings
from scipy.signal import find_peaks, savgol_filter
from collections import deque

# Suppress warnings and unnecessary output
warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
cv2.setLogLevel(0)

class WorkoutAnalyzer:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=2,
            smooth_landmarks=True,
            enable_segmentation=False,  # Disable segmentation to reduce output
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        self.mp_drawing = mp.solutions.drawing_utils
        
        # Exercise thresholds and parameters
        self.squat_thresholds = {
            'knee_angle_min': 90,
            'knee_angle_max': 160,
            'depth_threshold': 0.15,
            'form_tolerance': 0.1
        }
        
        self.pushup_thresholds = {
            'elbow_angle_min': 70,
            'elbow_angle_max': 160,
            'body_alignment_tolerance': 0.08,
            'rom_threshold': 60
        }
        
    def calculate_angle(self, a, b, c):
        """Calculate angle between three points with improved precision"""
        try:
            a = np.array(a)
            b = np.array(b)
            c = np.array(c)
            
            ba = a - b
            bc = c - b
            
            cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
            cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
            angle = np.arccos(cosine_angle)
            
            return np.degrees(angle)
        except:
            return 0.0
    
    def calculate_distance(self, point1, point2):
        """Calculate Euclidean distance between two points"""
        try:
            return np.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)
        except:
            return 0.0
    
    def smooth_data(self, data, window_length=5):
        """Apply smoothing filter to reduce noise"""
        try:
            if len(data) < window_length:
                return data
            if window_length % 2 == 0:
                window_length -= 1
            return savgol_filter(data, window_length, min(3, window_length-1))
        except:
            return data
    
    def detect_exercise_type(self, landmarks_sequence):
        """Enhanced exercise detection with multiple criteria"""
        try:
            if not landmarks_sequence:
                return "unknown"
                
            # Calculate movement metrics
            hip_movement = self.analyze_hip_movement(landmarks_sequence)
            knee_movement = self.analyze_knee_movement(landmarks_sequence)
            shoulder_movement = self.analyze_shoulder_movement(landmarks_sequence)
            elbow_movement = self.analyze_elbow_movement(landmarks_sequence)
            
            # Enhanced classification with confidence scores
            squat_confidence = 0
            pushup_confidence = 0
            lunge_confidence = 0
            
            # Squat detection
            if hip_movement > 0.2 and knee_movement > 0.25:
                squat_confidence += 40
            if hip_movement > 0.3:
                squat_confidence += 30
            if knee_movement > 0.4:
                squat_confidence += 30
                
            # Push-up detection
            if elbow_movement > 0.3 and shoulder_movement > 0.15:
                pushup_confidence += 40
            if self.check_horizontal_body_position(landmarks_sequence):
                pushup_confidence += 35
            if elbow_movement > 0.4:
                pushup_confidence += 25
                
            # Lunge detection
            if self.detect_asymmetric_leg_movement(landmarks_sequence):
                lunge_confidence += 60
            if hip_movement > 0.25 and knee_movement > 0.3:
                lunge_confidence += 40
                
            # Return exercise with highest confidence
            max_confidence = max(squat_confidence, pushup_confidence, lunge_confidence)
            
            if max_confidence < 50:
                return "unknown"
            elif squat_confidence == max_confidence:
                return "squat"
            elif pushup_confidence == max_confidence:
                return "push_up"
            else:
                return "lunge"
        except:
            return "unknown"
    
    def analyze_elbow_movement(self, landmarks_sequence):
        """Analyze elbow angle changes for push-up detection"""
        try:
            elbow_angles = []
            for landmarks in landmarks_sequence:
                if landmarks:
                    left_elbow_angle = self.calculate_angle(
                        [landmarks[11].x, landmarks[11].y],
                        [landmarks[13].x, landmarks[13].y],
                        [landmarks[15].x, landmarks[15].y]
                    )
                    elbow_angles.append(left_elbow_angle)
            
            if len(elbow_angles) < 2:
                return 0
                
            elbow_angles = self.smooth_data(elbow_angles)
            return (max(elbow_angles) - min(elbow_angles)) / 180.0
        except:
            return 0
    
    def check_horizontal_body_position(self, landmarks_sequence):
        """Check if body is in horizontal position"""
        try:
            horizontal_frames = 0
            total_frames = len(landmarks_sequence)
            
            for landmarks in landmarks_sequence:
                if landmarks:
                    shoulder_y = (landmarks[11].y + landmarks[12].y) / 2
                    hip_y = (landmarks[23].y + landmarks[24].y) / 2
                    
                    if abs(shoulder_y - hip_y) < 0.15:
                        horizontal_frames += 1
            
            return horizontal_frames / total_frames > 0.6
        except:
            return False
    
    def detect_asymmetric_leg_movement(self, landmarks_sequence):
        """Detect asymmetric leg movement for lunge detection"""
        try:
            left_knee_angles = []
            right_knee_angles = []
            
            for landmarks in landmarks_sequence:
                if landmarks:
                    left_knee = self.calculate_angle(
                        [landmarks[23].x, landmarks[23].y],
                        [landmarks[25].x, landmarks[25].y],
                        [landmarks[27].x, landmarks[27].y]
                    )
                    right_knee = self.calculate_angle(
                        [landmarks[24].x, landmarks[24].y],
                        [landmarks[26].x, landmarks[26].y],
                        [landmarks[28].x, landmarks[28].y]
                    )
                    left_knee_angles.append(left_knee)
                    right_knee_angles.append(right_knee)
            
            if len(left_knee_angles) < 2:
                return False
                
            left_range = max(left_knee_angles) - min(left_knee_angles)
            right_range = max(right_knee_angles) - min(right_knee_angles)
            
            return abs(left_range - right_range) > 30
        except:
            return False
    
    def analyze_hip_movement(self, landmarks_sequence):
        """Enhanced hip movement analysis"""
        try:
            hip_positions = []
            for landmarks in landmarks_sequence:
                if landmarks:
                    hip_y = (landmarks[23].y + landmarks[24].y) / 2
                    hip_positions.append(hip_y)
            
            if len(hip_positions) < 2:
                return 0
                
            hip_positions = self.smooth_data(hip_positions)
            return max(hip_positions) - min(hip_positions)
        except:
            return 0
    
    def analyze_knee_movement(self, landmarks_sequence):
        """Enhanced knee movement analysis"""
        try:
            knee_angles = []
            for landmarks in landmarks_sequence:
                if landmarks:
                    left_knee = self.calculate_angle(
                        [landmarks[23].x, landmarks[23].y],
                        [landmarks[25].x, landmarks[25].y],
                        [landmarks[27].x, landmarks[27].y]
                    )
                    right_knee = self.calculate_angle(
                        [landmarks[24].x, landmarks[24].y],
                        [landmarks[26].x, landmarks[26].y],
                        [landmarks[28].x, landmarks[28].y]
                    )
                    avg_knee = (left_knee + right_knee) / 2
                    knee_angles.append(avg_knee)
            
            if len(knee_angles) < 2:
                return 0
                
            knee_angles = self.smooth_data(knee_angles)
            return (max(knee_angles) - min(knee_angles)) / 180.0
        except:
            return 0
    
    def analyze_shoulder_movement(self, landmarks_sequence):
        """Enhanced shoulder movement analysis"""
        try:
            shoulder_positions = []
            for landmarks in landmarks_sequence:
                if landmarks:
                    shoulder_y = (landmarks[11].y + landmarks[12].y) / 2
                    shoulder_positions.append(shoulder_y)
            
            if len(shoulder_positions) < 2:
                return 0
                
            shoulder_positions = self.smooth_data(shoulder_positions)
            return max(shoulder_positions) - min(shoulder_positions)
        except:
            return 0
    
    def count_repetitions(self, landmarks_sequence, exercise_type):
        """Enhanced repetition counting with peak detection"""
        try:
            if exercise_type == "squat":
                return self.count_squat_reps(landmarks_sequence)
            elif exercise_type == "push_up":
                return self.count_pushup_reps(landmarks_sequence)
            elif exercise_type == "lunge":
                return self.count_lunge_reps(landmarks_sequence)
            else:
                return 0
        except:
            return 0
    
    def count_squat_reps(self, landmarks_sequence):
        """Enhanced squat counting using peak detection"""
        try:
            knee_angles = []
            for landmarks in landmarks_sequence:
                if landmarks:
                    left_knee = self.calculate_angle(
                        [landmarks[23].x, landmarks[23].y],
                        [landmarks[25].x, landmarks[25].y],
                        [landmarks[27].x, landmarks[27].y]
                    )
                    right_knee = self.calculate_angle(
                        [landmarks[24].x, landmarks[24].y],
                        [landmarks[26].x, landmarks[26].y],
                        [landmarks[28].x, landmarks[28].y]
                    )
                    avg_knee = (left_knee + right_knee) / 2
                    knee_angles.append(avg_knee)
            
            if len(knee_angles) < 10:
                return 0
                
            knee_angles = self.smooth_data(knee_angles, window_length=min(7, len(knee_angles)))
            
            peaks, _ = find_peaks(knee_angles, height=self.squat_thresholds['knee_angle_max'], distance=10)
            valleys, _ = find_peaks(-np.array(knee_angles), height=-self.squat_thresholds['knee_angle_min'], distance=10)
            
            return min(len(peaks), len(valleys))
        except:
            return 0
    
    def count_pushup_reps(self, landmarks_sequence):
        """Enhanced push-up counting"""
        try:
            elbow_angles = []
            for landmarks in landmarks_sequence:
                if landmarks:
                    left_elbow = self.calculate_angle(
                        [landmarks[11].x, landmarks[11].y],
                        [landmarks[13].x, landmarks[13].y],
                        [landmarks[15].x, landmarks[15].y]
                    )
                    right_elbow = self.calculate_angle(
                        [landmarks[12].x, landmarks[12].y],
                        [landmarks[14].x, landmarks[14].y],
                        [landmarks[16].x, landmarks[16].y]
                    )
                    avg_elbow = (left_elbow + right_elbow) / 2
                    elbow_angles.append(avg_elbow)
            
            if len(elbow_angles) < 10:
                return 0
                
            elbow_angles = self.smooth_data(elbow_angles, window_length=min(7, len(elbow_angles)))
            
            peaks, _ = find_peaks(elbow_angles, height=self.pushup_thresholds['elbow_angle_max'], distance=8)
            valleys, _ = find_peaks(-np.array(elbow_angles), height=-self.pushup_thresholds['elbow_angle_min'], distance=8)
            
            return min(len(peaks), len(valleys))
        except:
            return 0
    
    def count_lunge_reps(self, landmarks_sequence):
        """Count lunge repetitions"""
        try:
            left_knee_angles = []
            right_knee_angles = []
            
            for landmarks in landmarks_sequence:
                if landmarks:
                    left_knee = self.calculate_angle(
                        [landmarks[23].x, landmarks[23].y],
                        [landmarks[25].x, landmarks[25].y],
                        [landmarks[27].x, landmarks[27].y]
                    )
                    right_knee = self.calculate_angle(
                        [landmarks[24].x, landmarks[24].y],
                        [landmarks[26].x, landmarks[26].y],
                        [landmarks[28].x, landmarks[28].y]
                    )
                    left_knee_angles.append(left_knee)
                    right_knee_angles.append(right_knee)
            
            if len(left_knee_angles) < 10:
                return 0
                
            left_range = max(left_knee_angles) - min(left_knee_angles)
            right_range = max(right_knee_angles) - min(right_knee_angles)
            
            active_leg_angles = left_knee_angles if left_range > right_range else right_knee_angles
            active_leg_angles = self.smooth_data(active_leg_angles)
            
            peaks, _ = find_peaks(active_leg_angles, height=140, distance=10)
            valleys, _ = find_peaks(-np.array(active_leg_angles), height=-100, distance=10)
            
            return min(len(peaks), len(valleys))
        except:
            return 0
    
    def analyze_form(self, landmarks_sequence, exercise_type):
        """Enhanced form analysis with detailed feedback"""
        try:
            feedback = []
            form_score = 10.0
            
            if exercise_type == "squat":
                feedback, form_score = self.analyze_squat_form(landmarks_sequence)
            elif exercise_type == "push_up":
                feedback, form_score = self.analyze_pushup_form(landmarks_sequence)
            elif exercise_type == "lunge":
                feedback, form_score = self.analyze_lunge_form(landmarks_sequence)
            else:
                feedback = ["Exercise not recognized for detailed analysis"]
                form_score = 5.0
            
            return feedback, max(0.0, min(10.0, form_score))
        except:
            return ["Error analyzing form"], 5.0
    
    def analyze_squat_form(self, landmarks_sequence):
        """Enhanced squat form analysis"""
        try:
            feedback = []
            form_score = 10.0
            
            knee_cave_frames = 0
            back_lean_frames = 0
            depth_insufficient_frames = 0
            knee_forward_frames = 0
            
            total_frames = len(landmarks_sequence)
            
            for landmarks in landmarks_sequence:
                if landmarks:
                    # Knee alignment check
                    left_knee_x = landmarks[25].x
                    left_hip_x = landmarks[23].x
                    left_ankle_x = landmarks[27].x
                    
                    if left_knee_x < min(left_hip_x, left_ankle_x) - 0.02:
                        knee_cave_frames += 1
                    
                    if left_knee_x > left_ankle_x + 0.05:
                        knee_forward_frames += 1
                    
                    # Back posture check
                    shoulder = [(landmarks[11].x + landmarks[12].x) / 2, (landmarks[11].y + landmarks[12].y) / 2]
                    hip = [(landmarks[23].x + landmarks[24].x) / 2, (landmarks[23].y + landmarks[24].y) / 2]
                    
                    torso_angle = abs(np.arctan2(shoulder[1] - hip[1], shoulder[0] - hip[0]) * 180 / np.pi)
                    if torso_angle < 60:
                        back_lean_frames += 1
                    
                    # Depth check
                    hip_y = (landmarks[23].y + landmarks[24].y) / 2
                    knee_y = (landmarks[25].y + landmarks[26].y) / 2
                    
                    if hip_y < knee_y - 0.02:
                        depth_insufficient_frames += 1
            
            # Generate feedback
            if knee_cave_frames > total_frames * 0.15:
                feedback.append("Keep your knees aligned with your toes - avoid knee cave")
                form_score -= 2.5
            
            if knee_forward_frames > total_frames * 0.2:
                feedback.append("Keep your knees behind your toes")
                form_score -= 1.5
            
            if back_lean_frames > total_frames * 0.25:
                feedback.append("Keep your chest up and back straight")
                form_score -= 2.0
            
            if depth_insufficient_frames > total_frames * 0.3:
                feedback.append("Go deeper - hips should go below knee level")
                form_score -= 1.5
            
            if not feedback:
                feedback.append("Excellent squat form! Keep it up!")
            
            return feedback, form_score
        except:
            return ["Error analyzing squat form"], 5.0
    
    def analyze_pushup_form(self, landmarks_sequence):
        """Enhanced push-up form analysis"""
        try:
            feedback = []
            form_score = 10.0
            
            hip_sag_frames = 0
            hip_pike_frames = 0
            partial_rom_frames = 0
            head_position_frames = 0
            
            total_frames = len(landmarks_sequence)
            
            for landmarks in landmarks_sequence:
                if landmarks:
                    shoulder_y = (landmarks[11].y + landmarks[12].y) / 2
                    hip_y = (landmarks[23].y + landmarks[24].y) / 2
                    ankle_y = (landmarks[27].y + landmarks[28].y) / 2
                    
                    if hip_y > max(shoulder_y, ankle_y) + 0.03:
                        hip_sag_frames += 1
                    
                    if hip_y < min(shoulder_y, ankle_y) - 0.03:
                        hip_pike_frames += 1
                    
                    elbow_angle = self.calculate_angle(
                        [landmarks[11].x, landmarks[11].y],
                        [landmarks[13].x, landmarks[13].y],
                        [landmarks[15].x, landmarks[15].y]
                    )
                    
                    if elbow_angle > 110:
                        partial_rom_frames += 1
                    
                    nose_y = landmarks[0].y
                    if nose_y > shoulder_y + 0.05:
                        head_position_frames += 1
            
            # Generate feedback
            if hip_sag_frames > total_frames * 0.2:
                feedback.append("Keep your core tight - avoid hip sag")
                form_score -= 2.5
            
            if hip_pike_frames > total_frames * 0.2:
                feedback.append("Keep your body straight - avoid piking your hips")
                form_score -= 2.0
            
            if partial_rom_frames > total_frames * 0.3:
                feedback.append("Go lower - chest should nearly touch the ground")
                form_score -= 2.0
            
            if head_position_frames > total_frames * 0.25:
                feedback.append("Keep your head in neutral position")
                form_score -= 1.0
            
            if not feedback:
                feedback.append("Perfect push-up form! Well done!")
            
            return feedback, form_score
        except:
            return ["Error analyzing push-up form"], 5.0
    
    def analyze_lunge_form(self, landmarks_sequence):
        """Analyze lunge form"""
        try:
            feedback = []
            form_score = 10.0
            
            knee_forward_frames = 0
            torso_lean_frames = 0
            insufficient_depth_frames = 0
            
            total_frames = len(landmarks_sequence)
            
            for landmarks in landmarks_sequence:
                if landmarks:
                    left_knee_x = landmarks[25].x
                    left_ankle_x = landmarks[27].x
                    
                    if left_knee_x > left_ankle_x + 0.05:
                        knee_forward_frames += 1
                    
                    shoulder_x = (landmarks[11].x + landmarks[12].x) / 2
                    hip_x = (landmarks[23].x + landmarks[24].x) / 2
                    
                    if abs(shoulder_x - hip_x) > 0.08:
                        torso_lean_frames += 1
                    
                    front_knee_y = landmarks[25].y
                    back_knee_y = landmarks[26].y
                    
                    if min(front_knee_y, back_knee_y) > 0.7:
                        insufficient_depth_frames += 1
            
            if knee_forward_frames > total_frames * 0.2:
                feedback.append("Keep your front knee behind your toes")
                form_score -= 2.0
            
            if torso_lean_frames > total_frames * 0.25:
                feedback.append("Keep your torso upright")
                form_score -= 1.5
            
            if insufficient_depth_frames > total_frames * 0.3:
                feedback.append("Go deeper in your lunge")
                form_score -= 1.5
            
            if not feedback:
                feedback.append("Great lunge form!")
            
            return feedback, form_score
        except:
            return ["Error analyzing lunge form"], 5.0
    
    def analyze_video(self, video_path):
        """Enhanced video analysis with better error handling"""
        try:
            # Suppress OpenCV output
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                return {
                    "exerciseName": "error",
                    "repCount": 0,
                    "feedback": ["Could not open video file"],
                    "formScore": 0.0
                }
            
            landmarks_sequence = []
            frame_count = 0
            
            while cap.isOpened():
                success, image = cap.read()
                if not success:
                    break
                
                frame_count += 1
                
                # Resize for performance
                height, width = image.shape[:2]
                if width > 640:
                    scale = 640.0 / width
                    new_width = int(width * scale)
                    new_height = int(height * scale)
                    image = cv2.resize(image, (new_width, new_height))
                
                # Convert and process
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                results = self.pose.process(image_rgb)
                
                if results.pose_landmarks:
                    landmarks_sequence.append(results.pose_landmarks.landmark)
                else:
                    landmarks_sequence.append(None)
            
            cap.release()
            
            # Filter valid landmarks
            valid_landmarks = [lm for lm in landmarks_sequence if lm is not None]
            
            if not valid_landmarks:
                return {
                    "exerciseName": "unknown",
                    "repCount": 0,
                    "feedback": ["Could not detect pose in video"],
                    "formScore": 0.0
                }
            
            if len(valid_landmarks) < 30:
                return {
                    "exerciseName": "unknown",
                    "repCount": 0,
                    "feedback": ["Video too short for analysis"],
                    "formScore": 0.0
                }
            
            # Analyze workout
            exercise_type = self.detect_exercise_type(valid_landmarks)
            rep_count = self.count_repetitions(valid_landmarks, exercise_type)
            feedback, form_score = self.analyze_form(valid_landmarks, exercise_type)
            
            return {
                "exerciseName": exercise_type,
                "repCount": rep_count,
                "feedback": feedback,
                "formScore": round(form_score, 1),
                "analysisQuality": "high" if len(valid_landmarks) / frame_count > 0.8 else "medium"
            }
            
        except Exception as e:
            return {
                "exerciseName": "error",
                "repCount": 0,
                "feedback": [f"Analysis failed: {str(e)}"],
                "formScore": 0.0
            }

def main():
    try:
        if len(sys.argv) != 2:
            result = {"error": "Usage: python pose_analyzer.py <video_path>"}
            print(json.dumps(result), flush=True)
            sys.exit(1)
        
        video_path = sys.argv[1]
        analyzer = WorkoutAnalyzer()
        
        result = analyzer.analyze_video(video_path)
        print(json.dumps(result), flush=True)
        
    except Exception as e:
        result = {
            "exerciseName": "error",
            "repCount": 0,
            "feedback": [f"Analysis failed: {str(e)}"],
            "formScore": 0.0
        }
        print(json.dumps(result), flush=True)

if __name__ == "__main__":
    main()