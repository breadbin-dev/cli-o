import {logout} from "../header";
import {findIntellisense} from "./intellisense";
import {errMsg, uniqueId} from "../utils";


export async function doRequest(func, args, since) {
    return fetch(window.API_HOST + '/call/' + func, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({"function": func, "args": args, "since": since})
    });
}


export function command(uid, initialText, isShowing, onSubmit, onClear, getHistory, closeCommand, renameTab, dropTab, saveTabs, scrollToView) {
    return {
        focused: true,
        hover: false,
        disposed: false,
        text: "",
        errText: null,
        errX: -1,
        errY: -1,
        consoleShowing: isShowing,
        content: { body: "", type: "empty"},
        updatedDttm: null,
        firstResult: true,
        uid: uid,
        intellisenseTable: [],
        historyLoc: 0,
        suggestionLoc: 0,
        refreshHandler: null,
        inflightRequest: null,
        inHistory: false,
        inSuggestions: false,
        nextSuggestion: "",

        intellisense() {
            if ((this.focused || this.hover) && this.intellisenseTable.length !== 0)
                return this.intellisenseTable;
            else
                return null;
        },

        init() {
            if (initialText) {
                this.text = initialText;
                this.focused = false;
                this.runCommand();
            }
            else {
                this.$refs.commandLine.focus();
                this.focused = true;
            }
            this.$watch('text', value => {
                if (value === "") {
                    this.intellisenseTable = [];
                    this.nextSuggestion = "";
                }
                else {
                    this.intellisenseTable = findIntellisense(value);
                    if (this.intellisenseTable.length > 0)
                        this.nextSuggestion = this.intellisenseTable[0][0];
                    else
                        this.nextSuggestion = "";
                }
                this.inSuggestions = false;
                this.suggestionLoc = 0;
            });
            this.$watch("isShowing", s => {
                this.consoleShowing = s;
            })
        },

        destroy() {
            this.disposed = true;
            this.hover = false;
            this.focused = false;
        },

        onSuggest(suggestion = null, event = null) {
            if (event != null)
                event.preventDefault();

            if (suggestion == null)
                suggestion = this.nextSuggestion;

            if (suggestion != null)
                this.text = suggestion;
        },

        onHistory(up, event) {
            event.preventDefault();

            if (!this.inHistory && !this.inSuggestions) {
                if (up > 0)
                    this.inHistory = true;
                else if (this.intellisenseTable.length > 0)
                    this.inSuggestions = true;
            }

            if (this.inHistory) {
                let history = getHistory()
                this.historyLoc += up;
                let loc = history.length - this.historyLoc
                if (loc >= 0 && loc < history.length) {
                    this.text = history[loc];
                } else if (loc === history.length) {
                    this.text = ""
                } else {
                    this.historyLoc -= up;
                }

                if (this.historyLoc === 0) {
                    this.inHistory = false;
                }
            }

            if (this.inSuggestions) {
                this.suggestionLoc -= up;
                if (this.suggestionLoc < 0) {
                    this.suggestionLoc = this.intellisenseTable.length-1;
                } else if (this.suggestionLoc >= this.intellisenseTable.length) {
                    this.suggestionLoc = 0;
                }
                this.nextSuggestion = this.intellisenseTable[this.suggestionLoc][0]
            }
        },

        onEscape() {
            this.intellisenseTable = [];
            this.nextSuggestion = "";
            this.inSuggestions = false;
            this.suggestionLoc = 0;
        },

        async makeRequest(func, args, handler=null) {
            const reqId = uniqueId();
            this.inflightRequest = reqId;

            const response = await doRequest(func, args, this.updatedDttm);

            if (!response.ok) {
                if (response.status === 498) {
                    console.log("token invalid");
                    logout();
                }
                this.content = { body: errMsg(response), type: "err"};
            } else {
                let content = await response.text()
                content = JSON.parse(content)
                if (!handler) {
                    this.content = { body: content["result"], type: content["type"]};
                } else {
                    handler(content["result"])
                }
                this.updatedDttm = content["last_update"];

                if (this.firstResult) {
                    scrollToView();
                    this.firstResult = false;
                }

                let refreshPeriod = content["refresh_period"];
                if (refreshPeriod) {
                    setTimeout(async () => {
                        if (reqId === this.inflightRequest && !this.disposed) {
                            try {
                                const [func, args] = parseCmd(this.text);
                                await this.makeRequest(func, args, handler=this.refreshHandler)
                            } catch (e) {
                                this.content = { body: e.message, type: "err"};
                            }
                        }
                    }, refreshPeriod)
                }
            }
        },

        async runCommand(event, cmd=null) {
            if (cmd === null) {
                cmd = this.text;
                onSubmit(uid, cmd);
            }

            this.updatedDttm = null;
            this.hover = false;
            this.$refs.commandLine.blur();

            try {
                const [func, args] = parseCmd(cmd);
                if (func === "logout") {
                    logout();
                } else if (func === "clear") {
                    onClear();
                } else if (func === "help" || func === "") {
                    this.content = { body: [...window.intellisense].filter(([k, v]) => !k.includes(".")), type: "help"};
                } else if (func === "rename") {
                    renameTab(args);
                    closeCommand(uid);
                } else if (func === "drop") {
                    dropTab();
                } else if (func === "save") {
                    closeCommand(uid);
                    saveTabs();
                } else if (func === "history") {
                    this.content = { body: getHistory().map(x => [x, ""]), type: "help"};
                } else if (func.indexOf(".") === -1) {
                    let funcs = findIntellisense(func + ".");
                    if (funcs.length === 0) {
                        this.content = { body: "No such queue: " + func, type: "err"};
                    } else {
                        this.content = { body: funcs, type: "help"};
                    }
                } else {
                    this.content = { body: "waiting...", type: "text"};
                    await this.makeRequest(func, args)
                }
            } catch (e) {
                this.content = { body: e.message, type: "err"};
            }
        },

        onClose() {
            closeCommand(uid);
        },

        addRefreshHandler(refreshHandler) {
            this.refreshHandler = refreshHandler;
        },

        async backgroundFunction(event, cmd) {
            this.errText = null;
            try {
                const [func, args] = parseCmd(cmd);
                let response = await doRequest(func, args);
                if (!response.ok)
                    throw Error(errMsg(response));

                let result = await response.text();
                result = JSON.parse(result);
                if (result["type"] === "err")
                    throw Error(result["result"]);
            } catch (ex) {
                console.error(ex);
                this.errX = event.clientX + 'px';
                this.errY = event.clientY + 'px';
                this.errText = ex.message;
            }
        }
    }
}

export function parseCmd(cmd) {
    cmd = cmd.trim()
    const i = cmd.indexOf(' ')
    if (i === -1)
        return [cmd, ""]
    else
        return [cmd.substring(0, i), cmd.substring(i + 1).trim()]
}

export default command;