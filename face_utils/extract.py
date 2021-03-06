import argparse
import sys
from pathlib import Path

import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

import cv2
import yaml
from tqdm import tqdm
import logging

from ds_utils import image_processing
from ds_utils import video_utils

from face_utils import CONFIG_PATH
from face_utils.FaceDetector import FaceDetector, FaceExtractException


def frame_extract_fun(frame, frame_count, face_detector: FaceDetector, output_path: Path, step_mod: int):
    try:
        faces = face_detector.detect_faces(frame)
        for face_count, face in enumerate(faces):
            extracted_face = face_detector.extract_face(face)

            if frame_count % step_mod == 0:
                cv2.imwrite(str(output_path / "face_{:04d}_{:04d}.jpg".format(frame_count, face_count)),
                            extracted_face)
                frame_count += 1
    except FaceExtractException as e:
        logging.debug("Frame {}: {}".format(frame_count, e))
    except Exception as e:
        logging.error(e)
        raise


def main(_=None):
    logging.getLogger().setLevel(logging.INFO)

    parser = argparse.ArgumentParser(description='Extract Faces')

    parser.add_argument('-i', metavar='input_path', dest='input_path', required=True)
    parser.add_argument('-o', metavar='output_path', dest='output_path', required=True)
    parser.add_argument('-c', metavar='config_path', dest='config_path',
                        default=CONFIG_PATH)
    parser.add_argument('-v', dest='verbose', action='store_true')
    parser.set_defaults(verbose=False)
    parser.add_argument('--process-images', dest='process_images', action='store_true',
                        help="Run extraction on images in the given input dir")
    parser.set_defaults(process_images=False)
    parser.add_argument('-s', metavar='step_mod', dest='step_mod', default=1,
                        help="Save only face for frame where frame_num%step_mod == 0")

    args = parser.parse_args()
    input_path = Path(args.input_path)
    output_path = Path(args.output_path)
    process_images = args.process_images
    config_path = Path(args.config_path)
    step_mod = int(args.step_mod)
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    assert input_path.exists(), f"No such path: {input_path}"
    assert config_path.exists(), f"No such config file: {config_path}"

    if not output_path.exists():
        logging.info(f"Creating output dir: {output_path}")
        output_path.mkdir()

    with open(str(config_path), 'r') as ymlfile:
        cfg = yaml.load(ymlfile)

    face_detector = FaceDetector(cfg)
    frame_count = 0

    if process_images:
        # collected all image paths
        img_paths = image_processing.get_imgs_paths(input_path, as_str=False)

        logging.info("Running Face Extraction over images")
        # iterate over all collected image paths
        for img_path in tqdm(img_paths):
            frame_count += 1
            img = cv2.imread(str(img_path))
            frame_extract_fun(img, frame_count, face_detector, output_path, step_mod)
    # process video
    else:
        # get a valid file from given directory
        if input_path.is_dir():
            video_files = image_processing.get_imgs_paths(input_path, img_types=('*.gif', '*.webm', '*.mp4'), as_str=True)
            if not video_files:
                logging.error(f"No valid video files in: {input_path}")
                sys.exit(1)
            # for now just pick first one
            input_path = Path(video_files[0])

        logging.info("Running Face Extraction over video")

        video_utils.process_video(str(input_path), lambda frame, frame_count:
                                  frame_extract_fun(frame, frame_count, face_detector, output_path, step_mod))


if __name__ == "__main__":
    main(sys.argv[1:])
