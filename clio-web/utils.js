import { DateTime } from "luxon";

import { customAlphabet } from 'nanoid';

export const uniqueId = customAlphabet('abcdefghijklmnopqrstuvwxyz', 8);


export function errMsg(response) {
    let err = response.statusText;
    if (err === "")
        err = response.status + ": " + response.type;
    return err;
}

export function now_dttm(tz) {
    return DateTime.now().setZone(tz).toLocaleString(DateTime.TIME_24_SIMPLE);
}

export function clock(name, tz) {
    return {
        dttm: name + '/' + now_dttm(tz),
        init(){
            setInterval(() => {
                this.dttm = name + '/' + now_dttm(tz);
            }, 1000);
        }
    }
}

export function format(str, vars) {
    return str.replace(/{(\w+)}/g, (_, key) => vars[key] ?? '');
}

export default {};