import {uniqueId} from "./utils";


export function tabs() {
    let content = null;

    try {
        let storedContent = localStorage.getItem('tabContent');
        if (storedContent)
            content = JSON.parse(storedContent);

    } catch (ex) {
        console.error("Problem restoring tabs:", ex.message);
    }
    if (content === null)
        content = [{uid: uniqueId(), name: 'console', initialCommands: [], refreshId: 0, editName: false}]

    return {
        theme: window.SITE_THEME,
        tabs: content,
        currentTab: content[0].uid,
        addTab() {
            let newTab = {uid: uniqueId(), name: 'console', initialCommands: [], refreshId: 0, editName: false};
            this.tabs.push(newTab);
            this.currentTab = newTab.uid;
        },
        tabMenu() {
            return {
                open: false,
                saveTabs: this.saveTabs,
                dropTab: this.dropTab,
                editTabName: this.editTabName,
                outer_this: this,
                menuItems: ["save tabs", "rename tab", "drop tab"],
                toggle() { this.open ? this.close() : this.openMenu() },
                openMenu() {
                    this.open = true
                },
                close() {
                    this.open = false
                },
                choose(action) {
                    this.close()
                    if (action === 'save tabs') {
                        this.saveTabs();
                    } else if (action === 'drop tab') {
                        this.dropTab(this.outer_this.currentTab)
                    } else if (action === 'rename tab') {
                        this.editTabName(this.outer_this.currentTab)
                    }
                }
            }
        },
        refreshTab(uid) {
            let i = this.tabs.findIndex(t => t.uid === uid);
            if (i !== -1)
                this.tabs[i].refreshId += 1;
        },
        renameTab(uid, newName) {
            let i = this.tabs.findIndex(t => t.uid === uid);
            if (i !== -1) {
                this.tabs[i].name = newName;
                this.tabs[i].editName = false;
            }
        },
        editTabName(uid, newName) {
            let i = this.tabs.findIndex(t => t.uid === uid);
            if (i !== -1) {
                this.tabs[i].editName = true;
            }
        },
        dropTab(uid) {
            let i = this.tabs.findIndex(t => t.uid === uid);
            if (i !== -1) {
                this.tabs.splice(i, 1);
            }
        },
        saveTabs() {
            let content = [];
            for (const tab of this.tabs) {
                let docTab = document.querySelector('#console_' + tab.uid);
                let commands = Object.values(docTab.querySelectorAll(".command-input")).map(n => n.value).filter(n => n !== "save" && n !== "");
                content.push({uid: tab.uid, name: tab.name, initialCommands: commands, refreshId: 0});
                localStorage.setItem('tabContent', JSON.stringify(content));
                tab.initialCommands = commands;
            }
        }
    }
}