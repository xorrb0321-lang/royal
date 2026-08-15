"""YOLO를 이용한 강아지 탐지.

각 큐브맵 면 이미지에서 COCO "dog" 클래스를 탐지한다. GPU가 있으면 자동으로
CUDA를 사용한다(RTX 3050에서 잘 동작). ultralytics/torch는 무거우므로 지연 임포트한다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from .config import Config

logger = logging.getLogger(__name__)


@dataclass
class Detection:
    pano_id: str
    image_path: str
    face: str
    confidence: float
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2 (픽셀)


def resolve_device(requested: str | None) -> str:
    """사용할 디바이스 결정. None이면 GPU 가용 시 cuda, 아니면 cpu."""
    if requested:
        return requested
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda:0"
    except Exception:  # noqa: BLE001
        pass
    return "cpu"


class DogDetector:
    def __init__(self, config: Config):
        self.config = config
        self.device = resolve_device(config.device)
        logger.info("탐지 디바이스: %s", self.device)
        from ultralytics import YOLO

        self.model = YOLO(config.yolo_model)

    def detect_images(self, image_paths: list[Path], pano_id: str) -> list[Detection]:
        """여러 이미지에서 강아지 탐지 결과를 반환."""
        if not image_paths:
            return []

        detections: list[Detection] = []
        results = self.model.predict(
            source=[str(p) for p in image_paths],
            conf=self.config.dog_conf_threshold,
            classes=[self.config.dog_class_id],
            device=self.device,
            verbose=False,
        )
        for path, res in zip(image_paths, results):
            boxes = getattr(res, "boxes", None)
            if boxes is None or len(boxes) == 0:
                continue
            for box in boxes:
                conf = float(box.conf[0])
                xyxy = tuple(float(v) for v in box.xyxy[0].tolist())
                detections.append(
                    Detection(
                        pano_id=pano_id,
                        image_path=str(path),
                        face=Path(path).stem,
                        confidence=conf,
                        bbox=xyxy,  # type: ignore[arg-type]
                    )
                )
        return detections

    def detect_batch(self, images_by_pano: dict[str, list[Path]]) -> list[Detection]:
        all_dets: list[Detection] = []
        total = len(images_by_pano)
        for i, (pano_id, paths) in enumerate(images_by_pano.items(), start=1):
            if i % 50 == 0 or i == total:
                logger.info("탐지 진행 %d/%d 파노라마", i, total)
            all_dets.extend(self.detect_images(paths, pano_id))
        logger.info("탐지 완료: %d개 강아지 박스", len(all_dets))
        return all_dets
