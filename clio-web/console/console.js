import {uniqueId} from "../utils";


export function commandConsole(tabId, currentTab, initialCommands, refreshId, renameTab, dropTab, saveTabs) {

    return {
        commands: [],
        history: [],
        refreshId: refreshId,
        isShowing: tabId === currentTab,
        init() {
            this.addCommand();
            for (const cmd of initialCommands)
                this.addCommand(cmd);

            this.$watch('tab.refreshId', r => {
                this.onClear();
                for (const cmd of initialCommands)
                    this.addCommand(cmd);
            });

            this.$watch('tab.initialCommands', r => {
                initialCommands = r;
            });

            this.$watch('currentTab', t => {
                this.isShowing = tabId === t;
            });
        },
        scrollToView() {
            this.$nextTick(() => {
                this.$refs.consoleBody.scrollTop = this.$refs.consoleBody.scrollHeight;
            });
        },
        addCommand(initialText=null) {
            let lastCommand = {uid: uniqueId(), initialText: initialText}
            if (initialText) {
                let penultimateCommand = lastCommand;
                lastCommand = this.commands[this.commands.length - 1];
                let lastElement = document.getElementById(lastCommand.uid + "_input")
                if (lastElement != null && lastElement.value) {
                    penultimateCommand.initialText = lastElement.value + penultimateCommand.initialText;
                    lastElement.value = ""
                }
                this.commands[this.commands.length - 1] = penultimateCommand;
            }
            this.commands.push(lastCommand);
            this.scrollToView();
        },
        onSubmit(uid, cmd) {
            if (this.history.length === 0 || this.history[this.history.length - 1] !== cmd)
                this.history.push(cmd);

            if (uid === this.commands[this.commands.length - 1].uid)
                this.addCommand()
        },
        onClear() {
            this.commands = []
            this.addCommand()
        },
        clickCommand(cmd, event) {
            event.preventDefault();
            this.addCommand(cmd);
        },
        getHistory() {
            return this.history;
        },
        closeCommand(uid) {
            let i = this.commands.findIndex(c => c.uid === uid);
            if (i !== -1) {
                this.commands.splice(i, 1);
            }
        },
        renameTab(newName) {
            renameTab(tabId, newName);
        },
        dropTab() {
            dropTab(tabId);
        },
        saveTabs() {
            saveTabs();
        }
    }
}

export default commandConsole;
