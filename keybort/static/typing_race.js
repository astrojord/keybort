(() => {
    const root = document.querySelector("[data-typing-race]");
    if (matchMedia("(pointer: coarse)").matches) return;

    const part = (name) => root.querySelector(`[data-race-${name}]`);
    const runner = part("runner");
    const wordsEl = part("words");
    const input = part("input");
    const prompt = part("prompt");
    const textArea = part("text");
    const statusEl = part("status");
    const board = part("board");
    const history = part("history");
    const restart = part("restart");
    const total = part("total");
    const lengthButtons = [...root.querySelectorAll("[data-race-length]")];
    const stats = {
        wpm: part("wpm"),
        accuracy: part("accuracy"),
        time: part("time"),
        word: part("word"),
    };

    const CHARS_PER_WORD = 5;
    const RUNNING_WINDOW_MS = 500;
    const STUMBLE_MS = 180;
    const SPRITE_SCALE = 3;
    const SPRITE_WIDTH = 16;
    const SPRITE_HEIGHT = 13;
    const SPRITE_COLORS = {
        o: "#3b0a14",
        l: "#ff8a9b",
        h: "#f0304f",
        r: "#dc143c",
        d: "#9c0e2b",
        w: "#ffffff",
        k: "#1c0a0e",
        g: "#8a8a8a",
    };
    const SPRITE_TOP = ["...oooooooooo...", "..ollllllllllo.."];
    const SPRITE_BOTTOM = [".orrrrrrrrrrrro.", ".oddddddddddddo.", "..oooooooooooo.."];
    const SPRITE_FACES = {
        normal: [".ohhhhhhhhhhhho.", ".ohwwhhhhhhwwho.", ".ohwkhhhhhhwkho.", ".ohwkhhkkhhwkho."],
        happy: [".ohhhhhhhhhhhho.", ".ohhkhhhhhhkhho.", ".ohkhkhhhhkhkho.", ".ohhhhhkkhhhhho."],
        hurt: [".ohhhhhhhhhhhho.", ".ohkhkhhhhkhkho.", ".ohhkhhhhhhkhho.", ".ohkhkhkkhkhkho."],
    };
    const SPRITE_LEGS = {
        idle: ["....gg....gg....", "....gg....gg....", "....ggg...ggg..."],
        stride: ["....gg.....gg...", "...gg.......gg..", "..gg.........ggg"],
        passing: ["......gg.gg.....", "......gg.gg.....", "......gg.gg.....", "......ggg.ggg..."],
        landing: ["......gg..gg....", ".....gg....gg...", "....gg.....ggg.."],
        crossed: ["......gggg......", "....gg....gg....", "...ggg....ggg..."],
        tucked: ["....gg....gg...."],
    };
    const SPRITE_FRAMES = {
        idle: { face: "normal", legs: "idle" },
        run1: { face: "normal", legs: "stride" },
        run2: { face: "normal", legs: "passing" },
        run3: { face: "normal", legs: "landing" },
        stumble: { face: "hurt", legs: "crossed", lean: true },
        cheer: { face: "happy", legs: "tucked", lift: 3 },
    };
    const RUN_CYCLE = ["run1", "run2", "run3", "run2"];
    const SENTINEL = " ";
    const SHORT_WORD_MAX = 4;
    const LENGTH_STORAGE_KEY = "typingRaceWords";

    let wordCount = Number(root.dataset.wordCount);
    let caretTop = null;
    let runStep = 0;
    let stumbleUntil = 0;
    const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
    const spriteFrames = buildSprite();
    let shortWords = [];
    let longWords = [];
    let chars = [];
    let target = "";
    let position = 0;
    let correct = 0;
    let mistakes = 0;
    let extras = 0;
    let startedAt = null;
    let lastHitAt = 0;
    let finished = false;
    let ticker = null;

    const loadWords = (url) =>
        fetch(url)
            .then((response) => {
                if (!response.ok) throw new Error(response.statusText);
                return response.text();
            })
            .then((text) => text.split(/\s+/).filter(Boolean));

    const pick = (list) => list[Math.floor(Math.random() * list.length)];

    function randomWords() {
        const words = [];
        while (words.length < wordCount) {
            const word = pick(Math.random() < 0.5 ? shortWords : longWords);
            if (word !== words.at(-1)) words.push(word);
        }
        return words;
    }

    function render(words) {
        wordsEl.replaceChildren();
        chars = [];
        words.forEach((word) => {
            const wordEl = document.createElement("span");
            wordEl.className = "race-word";
            for (const char of `${word} `) {
                const charEl = document.createElement("span");
                charEl.className = "race-char";
                charEl.textContent = char;
                wordEl.append(charEl);
                chars.push(charEl);
            }
            wordsEl.append(wordEl);
        });
        target = words.join(" ");
    }

    const elapsed = () => (startedAt === null ? 0 : performance.now() - startedAt);

    const wpm = (characters, ms) => (ms > 0 ? characters / CHARS_PER_WORD / (ms / 60000) : 0);

    const accuracy = () => (correct + mistakes > 0 ? (100 * correct) / (correct + mistakes) : 100);

    const wordsDone = () => {
        if (position >= target.length) return wordCount;
        return target.slice(0, position).split(" ").length - 1;
    };

    function showStats(ms) {
        stats.wpm.textContent = Math.round(wpm(correct, ms));
        stats.accuracy.textContent = Math.round(accuracy());
        stats.time.textContent = (ms / 1000).toFixed(1);
        stats.word.textContent = wordsDone();
    }

    function tick() {
        showStats(elapsed());
        updateSprite();
    }

    function stopTicker() {
        clearInterval(ticker);
        ticker = null;
    }

    function moveRunner() {
        runner.style.setProperty("--race-progress", target.length ? position / target.length : 0);
    }

    function spriteRows({ face, legs, lift = 0, lean = false }) {
        let body = [...SPRITE_TOP, ...SPRITE_FACES[face], ...SPRITE_BOTTOM];
        if (lean) body = body.map((row) => `${row.slice(1)}.`);
        const rows = [...body, ...SPRITE_LEGS[legs]];
        const blank = ".".repeat(SPRITE_WIDTH);
        for (let count = 0; count < lift; count += 1) rows.push(blank);
        while (rows.length < SPRITE_HEIGHT) rows.unshift(blank);
        return rows;
    }

    function buildSprite() {
        const svgNamespace = "http://www.w3.org/2000/svg";
        const svg = document.createElementNS(svgNamespace, "svg");
        svg.setAttribute("viewBox", `0 0 ${SPRITE_WIDTH} ${SPRITE_HEIGHT}`);
        svg.setAttribute("width", SPRITE_WIDTH * SPRITE_SCALE);
        svg.setAttribute("height", SPRITE_HEIGHT * SPRITE_SCALE);
        const frames = {};
        for (const [name, spec] of Object.entries(SPRITE_FRAMES)) {
            const group = document.createElementNS(svgNamespace, "g");
            const shapes = {};
            spriteRows(spec).forEach((row, y) => {
                [...row].forEach((pixel, x) => {
                    if (pixel === ".") return;
                    shapes[pixel] = `${shapes[pixel] ?? ""}M${x} ${y}h1v1h-1z`;
                });
            });
            for (const [pixel, shape] of Object.entries(shapes)) {
                const path = document.createElementNS(svgNamespace, "path");
                path.setAttribute("d", shape);
                path.setAttribute("fill", SPRITE_COLORS[pixel]);
                group.append(path);
            }
            svg.append(group);
            frames[name] = group;
        }
        runner.replaceChildren(svg);
        return frames;
    }

    function setSpriteFrame(name) {
        for (const [frameName, group] of Object.entries(spriteFrames)) {
            group.toggleAttribute("data-active", frameName === name);
        }
    }

    function updateSprite() {
        const now = performance.now();
        if (now < stumbleUntil) {
            setSpriteFrame("stumble");
        } else if (!reducedMotion.matches && now - lastHitAt < RUNNING_WINDOW_MS) {
            runStep += 1;
            setSpriteFrame(RUN_CYCLE[runStep % RUN_CYCLE.length]);
        } else {
            setSpriteFrame("idle");
        }
    }

    function stumble() {
        if (reducedMotion.matches) return;
        stumbleUntil = performance.now() + STUMBLE_MS;
        setSpriteFrame("stumble");
    }

    async function save(ms) {
        if (correct === 0) {
            statusEl.textContent = "No correct keys, so this result wasn't saved.";
            return;
        }
        statusEl.textContent = "Saving…";
        const body = new URLSearchParams({
            keyboard: board.value,
            word_count: wordCount,
            characters: correct,
            mistakes,
            duration_ms: Math.round(ms),
        });
        try {
            const response = await fetch(root.dataset.saveUrl, {
                method: "POST",
                headers: { "X-CSRFToken": root.dataset.csrf },
                body,
                redirect: "manual",
            });
            if (response.type === "opaqueredirect") {
                statusEl.textContent = "Signed out, so this result wasn't saved.";
                return;
            }
            if (!response.ok) throw new Error(response.statusText);
            history.innerHTML = await response.text();
            statusEl.textContent = "Saved.";
        } catch (_) {
            statusEl.textContent = "Couldn't save this result.";
        }
    }

    function finish() {
        const ms = elapsed();
        finished = true;
        stopTicker();
        showStats(ms);
        setSpriteFrame("cheer");
        runner.toggleAttribute("data-finished", true);
        delete chars[target.length].dataset.state;
        statusEl.textContent = "";
        board.disabled = false;
        save(ms);
    }

    function start() {
        startedAt = performance.now();
        prompt.textContent = "Click here to keep typing";
        board.disabled = true;
        ticker = setInterval(tick, 100);
    }

    const wordStart = (index) => target.lastIndexOf(" ", index - 1) + 1;

    const isMissed = (index) => ["wrong", "skipped"].includes(chars[index].dataset.state);

    function hasMisses(start, end) {
        for (let index = start; index < end; index += 1) {
            if (isMissed(index)) return true;
        }
        return false;
    }

    function scrollToCaret() {
        const top = chars[position].offsetTop;
        if (top === caretTop) return;
        caretTop = top;
        const lineHeight = parseFloat(getComputedStyle(wordsEl).lineHeight);
        wordsEl.scrollTop = Math.max(0, top - lineHeight);
    }

    function syncProgress() {
        moveRunner();
        scrollToCaret();
        chars[position].dataset.state = extras > 0 ? "extra" : "current";
        statusEl.textContent = position === target.length ? "Press space to finish." : "";
    }

    function advance() {
        lastHitAt = performance.now();
        if (position === target.length && !hasMisses(wordStart(position), position)) {
            moveRunner();
            finish();
            return;
        }
        syncProgress();
    }

    function mark(state) {
        chars[position].dataset.state = state;
        position += 1;
    }

    function skipWord() {
        while (position < target.length && target[position] !== " ") {
            mistakes += 1;
            mark("skipped");
        }
        stumble();
        if (position === target.length) {
            moveRunner();
            finish();
            return;
        }
        correct += 1;
        mark("done");
        advance();
    }

    function realign(char) {
        let runStart = position;
        while (runStart > 0 && chars[runStart - 1].dataset.state === "wrong") runStart -= 1;
        for (let index = runStart; index < position; index += 1) {
            if (target[index] !== char) continue;
            delete chars[position].dataset.state;
            for (let cleared = index + 1; cleared < position; cleared += 1) {
                delete chars[cleared].dataset.state;
            }
            chars[index].dataset.state = "done";
            correct += 1;
            position = index + 1;
            advance();
            return true;
        }
        return false;
    }

    function dropLetter() {
        mistakes += 1;
        mark("skipped");
        correct += 1;
        mark("done");
        stumble();
        advance();
    }

    function handleChar(char) {
        if (finished || !target) return;
        const expected = target[position];
        const atEnd = position === target.length;
        const atWordStart = position === 0 || target[position - 1] === " ";
        if (char === " " && expected !== " " && !atEnd && atWordStart) return;
        if (startedAt === null) start();

        if (char !== " " && char !== expected && extras === 0 && realign(char)) return;
        if (char !== " " && expected !== " " && char !== expected && target[position + 1] === char) {
            dropLetter();
            return;
        }
        if (char === " " && atEnd) {
            finish();
            return;
        }
        if (char === " " && expected !== " ") {
            skipWord();
            return;
        }
        if ((expected === " " || atEnd) && char !== " ") {
            mistakes += 1;
            extras += 1;
            chars[position].dataset.state = "extra";
            stumble();
            return;
        }
        if (char === expected) {
            correct += 1;
            extras = 0;
            mark("done");
        } else {
            mistakes += 1;
            mark("wrong");
            stumble();
        }
        advance();
    }

    function returnToPreviousWord() {
        const spaceIndex = position - 1;
        const start = wordStart(spaceIndex);
        if (!hasMisses(start, spaceIndex)) return;
        delete chars[position].dataset.state;
        delete chars[spaceIndex].dataset.state;
        correct -= 1;
        position = spaceIndex;
        while (position > start && chars[position - 1].dataset.state === "skipped") {
            position -= 1;
            delete chars[position].dataset.state;
        }
        syncProgress();
    }

    function backspace() {
        if (finished || startedAt === null) return;
        if (extras > 0) {
            extras -= 1;
            syncProgress();
            return;
        }
        if (position === 0) return;
        if (target[position - 1] === " ") {
            returnToPreviousWord();
            return;
        }
        delete chars[position].dataset.state;
        position -= 1;
        if (chars[position].dataset.state === "done") correct -= 1;
        delete chars[position].dataset.state;
        syncProgress();
    }

    function deleteWord() {
        extras = 0;
        if (position === 0 || target[position - 1] === " ") backspace();
        while (!finished && startedAt !== null && position > 0 && target[position - 1] !== " ") {
            backspace();
        }
        if (!finished && startedAt !== null) syncProgress();
    }

    function resetInput() {
        input.value = SENTINEL;
        input.setSelectionRange(1, 1);
    }

    function newRace() {
        if (!shortWords.length) return;
        stopTicker();
        position = 0;
        correct = 0;
        mistakes = 0;
        extras = 0;
        startedAt = null;
        lastHitAt = 0;
        finished = false;
        prompt.textContent = "Click here to start typing";
        resetInput();
        statusEl.textContent = "";
        board.disabled = false;
        runner.removeAttribute("data-finished");
        stumbleUntil = 0;
        setSpriteFrame("idle");
        render(randomWords());
        chars[0].dataset.state = "current";
        caretTop = null;
        wordsEl.scrollTop = 0;
        moveRunner();
        showStats(0);
    }

    input.addEventListener("input", (event) => {
        const inputType = event.inputType ?? "";
        const typed = input.value.replace(SENTINEL, "");
        const sentinelGone = !input.value.includes(SENTINEL);
        resetInput();
        if (inputType === "deleteContentBackward") {
            backspace();
        } else if (inputType.startsWith("delete")) {
            deleteWord();
        } else if (sentinelGone && !typed) {
            backspace();
        } else {
            for (const char of typed) handleChar(char.toLowerCase());
        }
    });

    for (const eventName of ["focus", "click"]) {
        input.addEventListener(eventName, () => input.setSelectionRange(1, 1));
    }

    input.addEventListener("keydown", (event) => {
        if (event.key === "Escape" || (event.key === "Enter" && finished)) {
            event.preventDefault();
            newRace();
        }
    });

    function setLength(count) {
        wordCount = count;
        total.textContent = count;
        for (const button of lengthButtons) {
            const selected = Number(button.dataset.raceLength) === count;
            button.dataset.variant = selected ? "secondary" : "ghost";
            button.setAttribute("aria-pressed", selected);
        }
    }

    function storedLength() {
        try {
            return Number(localStorage.getItem(LENGTH_STORAGE_KEY));
        } catch (_) {
            return 0;
        }
    }

    for (const button of lengthButtons) {
        button.addEventListener("click", () => {
            const count = Number(button.dataset.raceLength);
            setLength(count);
            try {
                localStorage.setItem(LENGTH_STORAGE_KEY, count);
            } catch (_) {}
            newRace();
            input.focus();
        });
    }

    if (lengthButtons.some((button) => Number(button.dataset.raceLength) === storedLength())) {
        setLength(storedLength());
    }

    textArea.addEventListener("click", () => input.focus());

    restart.addEventListener("click", () => {
        newRace();
        input.focus();
    });

    input.disabled = true;
    prompt.textContent = "Loading words…";
    loadWords(root.dataset.words)
        .then((words) => {
            shortWords = words.filter((word) => word.length <= SHORT_WORD_MAX);
            longWords = words.filter((word) => word.length > SHORT_WORD_MAX);
            input.disabled = false;
            newRace();
        })
        .catch(() => {
            prompt.textContent = "Couldn't load the word list.";
        });
})();
