---
name: cleanup-chrome
description: Kill orphaned chromedriver and headless Chrome processes left over from failed Selenium test runs. Use when Selenium tests mass-fail with Connection reset or TimeoutException, when the system feels sluggish during test runs, or when the user mentions /cleanup-chrome. Also use proactively before running frontend acceptance tests if previous runs were interrupted or stopped.
---

# Clean Up Orphaned Chrome Processes

Failed or interrupted Selenium test runs leave behind chromedriver and headless Chrome processes. These accumulate and exhaust system resources, causing new Selenium tests to fail with `Connection reset` / `TimeoutException` on the Chrome DevTools WebSocket.

**NEVER kill by executable name (`taskkill /IM chromedriver.exe /F` or `/IM chrome.exe
/F`)** — this project's `.claude/rules/infrastructure.md` bans it outright: it kills
every instance system-wide, including other Claude sessions' active Selenium runs and
the user's own open browser windows. Kill only specific orphaned PIDs, identified by
process tree, never by name.

## Action

1. **Identify orphaned processes by PID**, not name. An orphan is a `chromedriver.exe`
   or `chrome.exe` process whose parent PID no longer exists (the parent test run died,
   the child didn't get cleaned up):
   ```powershell
   $live = Get-CimInstance Win32_Process | Where-Object { $_.Name -in 'chromedriver.exe','chrome.exe' }
   $livePids = $live.ProcessId
   $orphans = $live | Where-Object { $_.ParentProcessId -notin $livePids -and -not (Get-Process -Id $_.ParentProcessId -ErrorAction SilentlyContinue) }
   $orphans | Select-Object ProcessId, Name, ParentProcessId
   ```

2. **Report the orphan list to the user before killing anything** — show PID, name,
   count. If the count is 0, stop here; there is nothing to clean up (do not fall back
   to a blanket kill).

3. **Kill only those specific PIDs:**
   ```powershell
   $orphans | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
   ```

4. **Re-run step 1** to confirm the orphan count reached 0 — a chromedriver parent
   exiting can leave a fresh orphaned chrome.exe child; one or two more rounds may be
   needed. Never widen the kill to "any chrome.exe" if orphans persist — investigate why
   instead (e.g. a chromedriver process still alive but hung, which is a different fix).

5. **Clean locked test output** if it exists:
   ```bash
   rm -rf acceptance/build/test-results/frontendTest/binary 2>/dev/null
   ```

## Output

Report how many orphaned processes were found and killed (by PID), and confirm no
running Selenium session or the user's own browser was touched.
