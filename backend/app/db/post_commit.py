from collections.abc import Awaitable, Callable

from sqlmodel.ext.asyncio.session import AsyncSession

POST_COMMIT_HOOKS_KEY = "post_commit_hooks"

PostCommitHook = Callable[[], Awaitable[None]]


def add_post_commit_hook(session: AsyncSession, hook: PostCommitHook) -> None:
    hooks = session.info.setdefault(POST_COMMIT_HOOKS_KEY, [])
    hooks.append(hook)


def pop_post_commit_hooks(session: AsyncSession) -> list[PostCommitHook]:
    hooks = session.info.pop(POST_COMMIT_HOOKS_KEY, [])
    return [hook for hook in hooks if callable(hook)]
