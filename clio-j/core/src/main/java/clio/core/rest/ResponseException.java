package clio.core.rest;

import static clio.core.Strings.f;

public class ResponseException extends ConnectionException {
    private final int code;
    private final String reason;

    public ResponseException(int code, String reason) {
        super(f("[{}]: {}", code, reason));
        this.code = code;
        this.reason = reason;
    }

    public int code() {
        return code;
    }

    public String reason() {
        return reason;
    }
}
