"""
任务管理路由
"""

import uuid
import json
import time
import threading
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from sse_starlette.sse import EventSourceResponse

from app.schemas.task import TaskCreate, TaskResponse, TaskStatus
from app.config import get_settings


router = APIRouter(prefix="/tasks", tags=["任务管理"])

# 任务存储（内存，生产环境可换 Redis）
tasks: Dict[str, Dict[str, Any]] = {}

# 任务日志缓冲
task_logs: Dict[str, list] = {}


def serialize_task(task_data: Dict[str, Any]) -> Dict[str, Any]:
    """移除不可序列化字段"""
    safe_data = dict(task_data)
    safe_data.pop("stop_event", None)
    return safe_data


def log_task_event(task_id: str, level: str, message: str):
    """记录任务日志"""
    if task_id not in task_logs:
        task_logs[task_id] = []

    task_logs[task_id].append({
        "task_id": task_id,
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "message": message,
    })

    # 保留最近 1000 条日志
    if len(task_logs[task_id]) > 1000:
        task_logs[task_id] = task_logs[task_id][-1000:]


@router.post("/", response_model=TaskResponse)
async def create_task(task: TaskCreate, background_tasks: BackgroundTasks):
    """
    创建并启动注册任务
    """
    settings = get_settings()
    running_count = sum(1 for t in tasks.values() if t.get("status") == TaskStatus.RUNNING)
    if running_count >= settings.CONCURRENT_TASKS:
        raise HTTPException(status_code=429, detail="当前运行任务已达并发上限")

    schedule_enabled = task.schedule_enabled
    interval_hours = task.interval_hours
    run_now = task.run_now

    if schedule_enabled and (interval_hours is None or interval_hours <= 0):
        raise HTTPException(status_code=400, detail="定时任务需要有效的间隔小时数")

    task_id = str(uuid.uuid4())[:8]

    upload_mode = task.upload_mode
    tasks[task_id] = {
        "id": task_id,
        "status": TaskStatus.RUNNING,
        "count": task.count,
        "upload_mode": upload_mode,
        "schedule_enabled": schedule_enabled,
        "interval_hours": interval_hours,
        "next_run_at": None,
        "success_count": 0,
        "fail_count": 0,
        "total_time": 0.0,
        "avg_time": 0.0,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "stop_event": threading.Event(),
    }

    task_logs[task_id] = []
    log_task_event(task_id, "INFO", f"任务已创建，目标: {task.count} 个账号")

    # 在后台启动注册任务
    if schedule_enabled:
        background_tasks.add_task(
            run_scheduled_task,
            task_id,
            task.count,
            upload_mode,
            interval_hours,
            run_now,
        )
    else:
        background_tasks.add_task(run_registration_task, task_id, task.count, upload_mode)

    return serialize_task(tasks[task_id])


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """
    查询任务状态
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    return serialize_task(tasks[task_id])


@router.delete("/{task_id}")
async def stop_task(task_id: str):
    """
    停止任务
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    stop_event = tasks[task_id].get("stop_event")
    if stop_event and not stop_event.is_set():
        stop_event.set()

    tasks[task_id]["status"] = TaskStatus.STOPPED
    tasks[task_id]["updated_at"] = datetime.now()
    log_task_event(task_id, "WARN", "任务已手动停止")

    return {"message": "任务已停止", "task": serialize_task(tasks[task_id])}


@router.get("/{task_id}/logs")
async def get_task_logs(task_id: str):
    """
    获取任务日志 (SSE 流式)
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    async def log_generator():
        """日志流生成器"""
        last_index = 0

        while True:
            logs = task_logs.get(task_id, [])

            # 发送新日志
            for log in logs[last_index:]:
                yield {"event": "log", "data": json.dumps(log, ensure_ascii=False)}

            last_index = len(logs)

            # 检查任务是否结束
            task_status = tasks[task_id].get("status")
            if task_status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.STOPPED]:
                yield {"event": "status", "data": task_status}
                break

            await asyncio.sleep(0.5)

    return EventSourceResponse(log_generator())


def run_registration_task(
    task_id: str,
    count: int,
    upload_mode: Optional[str] = None,
    finalize_status: bool = True,
):
    """
    后台执行注册任务
    从 worker 模块调用注册逻辑
    注册完成后自动上传到远程服务器（如已配置）
    """
    from app.worker.register import run_batch_registration

    settings = get_settings()

    def progress_callback(progress_data: dict):
        """进度回调"""
        tasks[task_id].update({
            "success_count": progress_data.get("success", 0),
            "fail_count": progress_data.get("fail", 0),
            "total_time": progress_data.get("total_time", 0),
            "avg_time": progress_data.get("avg_time", 0),
            "updated_at": datetime.now(),
        })

        log_msg = progress_data.get("message", "")
        if log_msg:
            log_task_event(task_id, "INFO", log_msg)

    try:
        log_task_event(task_id, "INFO", f"开始执行注册任务...")

        result = run_batch_registration(
            count=count,
            log_callback=lambda msg: log_task_event(task_id, "INFO", msg),
            progress_callback=progress_callback,
            stop_event=tasks[task_id].get("stop_event"),
        )

        # 更新最终状态
        if result.get("stopped") or tasks[task_id].get("status") == TaskStatus.STOPPED:
            tasks[task_id].update({
                "status": TaskStatus.STOPPED,
                "success_count": result.get("success", 0),
                "fail_count": result.get("fail", 0),
                "total_time": result.get("total_time", 0),
                "avg_time": result.get("avg_time", 0),
                "updated_at": datetime.now(),
            })
            log_task_event(task_id, "WARN", "任务已停止，结束注册流程")
            return

        if finalize_status:
            tasks[task_id].update({
                "status": TaskStatus.COMPLETED if result.get("success", 0) > 0 else TaskStatus.FAILED,
                "success_count": result.get("success", 0),
                "fail_count": result.get("fail", 0),
                "total_time": result.get("total_time", 0),
                "avg_time": result.get("avg_time", 0),
                "updated_at": datetime.now(),
            })
        else:
            tasks[task_id].update({
                "status": TaskStatus.RUNNING,
                "success_count": result.get("success", 0),
                "fail_count": result.get("fail", 0),
                "total_time": result.get("total_time", 0),
                "avg_time": result.get("avg_time", 0),
                "updated_at": datetime.now(),
            })

        log_task_event(task_id, "OK", f"任务完成! 成功: {result.get('success', 0)}, 失败: {result.get('fail', 0)}")

        # 任务成功后上传到远程服务器
        if result.get("success", 0) > 0 and settings.UPLOAD_API_HOST:
            if settings.UPLOAD_ADMIN_KEY:
                log_task_event(task_id, "INFO", f"正在上传到远程服务器...")
                from app.utils.uploader import upload_to_remote
                upload_result = upload_to_remote(
                    api_host=settings.UPLOAD_API_HOST,
                    admin_key=settings.UPLOAD_ADMIN_KEY,
                    mode=upload_mode or settings.UPLOAD_MODE,
                )
                if upload_result.get("success"):
                    log_task_event(task_id, "OK", f"已上传到远程服务器: {upload_result.get('message', '')}")
                else:
                    log_task_event(task_id, "ERROR", f"上传失败: {upload_result.get('message', '')}")
            else:
                log_task_event(task_id, "WARN", f"未配置远程管理员密钥，跳过上传")

    except Exception as e:
        tasks[task_id]["status"] = TaskStatus.FAILED
        tasks[task_id]["updated_at"] = datetime.now()
        log_task_event(task_id, "ERROR", f"任务异常: {str(e)}")


def run_scheduled_task(
    task_id: str,
    count: int,
    upload_mode: Optional[str],
    interval_hours: float,
    run_now: bool = True,
):
    """
    定时循环执行注册任务
    """
    log_task_event(task_id, "INFO", f"定时任务已启动，间隔: {interval_hours} 小时")

    loop_count = 0
    while True:
        stop_event = tasks[task_id].get("stop_event")
        if stop_event and stop_event.is_set():
            tasks[task_id]["status"] = TaskStatus.STOPPED
            tasks[task_id]["updated_at"] = datetime.now()
            log_task_event(task_id, "WARN", "定时任务已停止")
            return

        loop_count += 1
        should_run = run_now or loop_count > 1
        if should_run:
            log_task_event(task_id, "INFO", f"开始第 {loop_count} 次定时任务")
            run_registration_task(task_id, count, upload_mode, finalize_status=False)
            log_task_event(task_id, "INFO", f"第 {loop_count} 次任务完成")
            stop_event = tasks[task_id].get("stop_event")
            if stop_event and stop_event.is_set():
                tasks[task_id]["status"] = TaskStatus.STOPPED
                tasks[task_id]["updated_at"] = datetime.now()
                log_task_event(task_id, "WARN", "定时任务已停止")
                return

        next_run = datetime.now() + timedelta(hours=interval_hours)
        tasks[task_id]["next_run_at"] = next_run
        tasks[task_id]["updated_at"] = datetime.now()
        log_task_event(task_id, "INFO", f"下一次任务时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")

        remaining_seconds = int(interval_hours * 3600)
        while remaining_seconds > 0:
            stop_event = tasks[task_id].get("stop_event")
            if stop_event and stop_event.is_set():
                tasks[task_id]["status"] = TaskStatus.STOPPED
                tasks[task_id]["updated_at"] = datetime.now()
                log_task_event(task_id, "WARN", "定时任务已停止")
                return
            time.sleep(1)
            remaining_seconds -= 1
