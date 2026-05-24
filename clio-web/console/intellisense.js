import {logout} from "../header";
import {errMsg} from "../utils";

function countChars(str, char) {
    let count = 0;
    for (let i = 0; i < str.length; i++) {
        if (str[i] === char)
            count++;
    }
    return count;
}


export function parseIntellisense(help) {
    const intellisense = new Map();
    intellisense.set("help", "display available commands/services")
    intellisense.set("clear", "clear screen")
    intellisense.set("history", "command history")
    intellisense.set("logout", "logout user")
    intellisense.set("rename", "rename tab")
    intellisense.set("drop", "drop tab")
    intellisense.set("save", "save tab")

    for (const [key, value] of Object.entries(JSON.parse(help))) {
        if (!key.startsWith("_"))
            intellisense.set(key, value)
    }
    return intellisense
}

export async function getIntellisense() {

    window.intellisense = new Map();
    window.intellisense.set("requested", "waiting...")

    try {
        const response = await fetch(window.API_HOST + '/describe', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`,
                'Content-Type': 'application/json'
            },
        });
        window.intellisense.clear()

        if (!response.ok) {
            if (response.status === 498) {
                console.log("token invalid");
                logout();
            }
            window.intellisense.set("problem", errMsg(response));
        } else {
            window.intellisense = parseIntellisense(await response.text());
        }
    } catch (e) {
        window.intellisense.clear()
        window.intellisense.set("problem", e.message);
    }
}

export function findIntellisense(func) {
    let intellisense = window.intellisense;
    let level = countChars(func, '.')
    let result = []
    let keys = []

    const space = func.indexOf(' ');
    if (space > -1)
        func = func.substring(0, space)

    if (level > 0) {
        const exactMatch = intellisense.get(func);
        if (exactMatch) {
            return [[null, exactMatch]];
        }
    }

    for (const key of intellisense.keys()) {
        if (key.startsWith(func) && level === countChars(key, '.')) {
            keys.push(key)
        }
    }
    if (keys.length > 0) {
        for (const key of keys) {
            result.push([key, intellisense.get(key).split("\n")[0]])
        }
    }
    return result
}

export default getIntellisense