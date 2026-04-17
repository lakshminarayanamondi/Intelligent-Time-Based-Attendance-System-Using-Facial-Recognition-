import os
import cv2
import numpy as np
import json


def train_model():
    """
    Train an LBPH face recognizer from images in the TrainingImage folder.

    Expected folder structure:
        TrainingImage/
            name_id/
                name.id.1.jpg
                name.id.2.jpg
                ...

    Output:
        TrainingImageLabel/Trainner.yml      - trained LBPH model
        TrainingImageLabel/id_mapping.json   - map numeric label -> original string ID
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    images_root = os.path.join(base_dir, "TrainingImage")
    label_dir = os.path.join(base_dir, "TrainingImageLabel")

    if not os.path.exists(images_root):
        print(f"[ERROR] TrainingImage folder not found at: {images_root}")
        return 1

    os.makedirs(label_dir, exist_ok=True)

    face_cascade_path = os.path.join(base_dir, "haarcascade_default.xml")
    if not os.path.exists(face_cascade_path):
        print(f"[ERROR] Haarcascade file not found at: {face_cascade_path}")
        return 1

    face_cascade = cv2.CascadeClassifier(face_cascade_path)

    recognizer = cv2.face.LBPHFaceRecognizer_create()

    face_samples = []
    numeric_labels = []
    id_mapping = {}  # numeric_label (str) -> original string ID

    current_label = 0

    print("[INFO] Scanning TrainingImage folder for faces...")

    for folder_name in os.listdir(images_root):
        folder_path = os.path.join(images_root, folder_name)
        if not os.path.isdir(folder_path):
            continue

        # Expect folder like "name_id"
        parts = folder_name.split("_")
        if len(parts) < 2:
            print(f"[WARNING] Skipping folder without expected pattern 'name_id': {folder_name}")
            continue

        original_id = parts[-1]  # everything after last underscore is ID

        # Assign numeric label for this original_id if not already assigned
        if original_id not in id_mapping.values():
            id_mapping[str(current_label)] = str(original_id)
            numeric_id_for_folder = current_label
            current_label += 1
        else:
            # Find existing numeric label for this ID
            for num_label_str, orig_id in id_mapping.items():
                if orig_id == str(original_id):
                    numeric_id_for_folder = int(num_label_str)
                    break

        print(f"[INFO] Processing folder {folder_name} -> ID '{original_id}' (label {numeric_id_for_folder})")

        for filename in os.listdir(folder_path):
            if not (filename.lower().endswith(".jpg") or filename.lower().endswith(".png")):
                continue

            img_path = os.path.join(folder_path, filename)
            img = cv2.imread(img_path)
            if img is None:
                print(f"[WARNING] Could not read image: {img_path}")
                continue

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            gray = cv2.equalizeHist(gray)

            faces = face_cascade.detectMultiScale(gray, 1.3, 5, minSize=(30, 30))
            if len(faces) == 0:
                print(f"[WARNING] No face detected in image: {img_path}")
                continue

            for (x, y, w, h) in faces:
                # Slight padding around face
                padding_x = int(w * 0.1)
                padding_y = int(h * 0.1)
                x_pad = max(0, x - padding_x)
                y_pad = max(0, y - padding_y)
                w_pad = w + 2 * padding_x
                h_pad = h + 2 * padding_y

                roi = gray[y_pad:y_pad + h_pad, x_pad:x_pad + w_pad]
                if roi.size == 0:
                    continue

                face_samples.append(roi)
                numeric_labels.append(numeric_id_for_folder)

    if not face_samples:
        print("[ERROR] No valid face samples found. Make sure you have captured images.")
        return 1

    print(f"[INFO] Training model with {len(face_samples)} samples...")
    recognizer.train(face_samples, np.array(numeric_labels))

    model_path = os.path.join(label_dir, "Trainner.yml")
    recognizer.save(model_path)
    print(f"[INFO] Model saved to {model_path}")

    mapping_path = os.path.join(label_dir, "id_mapping.json")
    with open(mapping_path, "w") as f:
        json.dump(id_mapping, f, indent=2)
    print(f"[INFO] ID mapping saved to {mapping_path}")

    print("[SUCCESS] Training completed successfully.")
    return 0


if __name__ == "__main__":
    exit_code = train_model()
    raise SystemExit(exit_code)

