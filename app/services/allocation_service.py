"""
Bay allocation using a FIFO Queue and a Priority Heap.

Only AVAILABLE bays enter the structures, so an occupied bay
can never be handed out. Priority bays (VIP / accessible) are
served first via a min-heap.
"""
from collections import deque
import heapq
from ..extensions import db
from ..models.parking_bay import ParkingBay, BayStatus


class BayAllocationService:

    @staticmethod
    def _build_queues():
        priority_heap = []
        normal_queue = deque()
        bays = (ParkingBay.query
                .filter_by(status=BayStatus.AVAILABLE)
                .order_by(ParkingBay.bay_number).all())
        for bay in bays:
            if bay.is_priority:
                heapq.heappush(priority_heap, (bay.bay_number, bay.id))
            else:
                normal_queue.append(bay.id)
        return priority_heap, normal_queue

    @classmethod
    def allocate_bay(cls):
        priority_heap, normal_queue = cls._build_queues()
        bay_id = None
        if priority_heap:
            _, bay_id = heapq.heappop(priority_heap)
        elif normal_queue:
            bay_id = normal_queue.popleft()
        if bay_id is None:
            return None
        bay = db.session.get(ParkingBay, bay_id)
        if bay is None or bay.status != BayStatus.AVAILABLE:
            return None
        return bay

    @staticmethod
    def mark_occupied(bay):
        bay.status = BayStatus.OCCUPIED

    @staticmethod
    def release_bay(bay):
        bay.status = BayStatus.AVAILABLE