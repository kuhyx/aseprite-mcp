import os
import subprocess
import tempfile
from pathlib import Path

import dotenv

_ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
dotenv.load_dotenv(dotenv_path=_ENV_PATH)


def lua_escape(s: str) -> str:
    """Escape a string for safe embedding inside a Lua double-quoted string literal."""
    return (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\0", "\\0")
    )


def reject_traversal(path: str) -> str | None:
    """Reject parent-directory traversal in a user-supplied path.

    Returns an error message string when the path contains a `..`
    component, or None when the path looks safe.

    The check works on raw path components, so it does not false-positive
    on filenames like `foo..bar.aseprite` (the previous `'..' in path`
    substring check did) and does not false-NEGATIVE on a `..` that
    normalization would cancel out. Normalizing first meant
    `foo/../bar.aseprite` was accepted while `../bar.aseprite` was
    rejected, i.e. the guard depended on whether the traversal happened to
    resolve back inside the tree -- not a security property. Absolute
    paths and tilde expansion are not rejected here: this function targets
    traversal only, not access scoping.
    """
    parts = path.replace("\\", "/").split("/")
    if ".." in parts:
        return "Invalid filename: parent directory traversal not allowed"
    return None


class AsepriteCommand:
    """Helper class for running Aseprite commands."""

    @staticmethod
    def run_command(args: list[str]) -> tuple[bool, str]:
        """Run an Aseprite command with proper error handling.

        Args:
            args: List of command arguments

        Returns:
            tuple: (success, output) where success is a boolean and output is the command output

        """
        try:
            cmd = [os.getenv("ASEPRITE_PATH", "aseprite"), *args]
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            return False, str(e.stderr)
        else:
            return True, result.stdout

    @staticmethod
    def execute_lua_script(
        script_content: str, filename: str | None = None
    ) -> tuple[bool, str]:
        """Execute a Lua script in Aseprite.

        Args:
            script_content: Lua script code to execute
            filename: Optional filename to open before executing script

        Returns:
            tuple: (success, output)

        """
        # Create a temporary file for the script
        with tempfile.NamedTemporaryFile(suffix=".lua", delete=False, mode="w") as tmp:
            tmp.write(script_content)
            script_path = tmp.name

        try:
            args = ["--batch"]
            if filename and Path(filename).exists():
                args.append(filename)
            args.extend(["--script", script_path])

            success, output = AsepriteCommand.run_command(args)
            return success, output
        finally:
            # Clean up the temporary script file
            Path(script_path).unlink()

    @staticmethod
    def execute_lua_script_checked(
        script_content: str, filename: str | None = None
    ) -> tuple[bool, str]:
        """Execute a Lua script and surface in-script errors.

        Scripts using this helper signal failure by printing a line
        starting with "ERROR:" (batch-mode scripts cannot affect the
        process exit code from Lua).

        Returns:
            tuple: (success, output) where output is the error message
            when an ERROR: line was printed, or the raw stdout otherwise.

        """
        success, output = AsepriteCommand.execute_lua_script(script_content, filename)
        if not success:
            return False, output
        for line in output.splitlines():
            if line.startswith("ERROR:"):
                return False, line[len("ERROR:") :]
        return True, output
