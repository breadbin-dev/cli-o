package clio.router;

import clio.core.ServiceStatus;
import clio.core.UserAuth;
import clio.core.db.ClickhouseSyntax;
import clio.core.db.Databases;
import clio.core.Strings;

import java.util.List;

public class RouterSchema {
    public static void main(String[] args) {
        var classes = List.of(
                ServiceStatus.class,
                UserAuth.User.class,
                TokenStore.UserToken.class
        );
        var syntax = new ClickhouseSyntax();
        var tables = new StringBuilder();
        for (var cls : classes)
            tables.append(Databases.tableForCls(cls, syntax));

        Strings.writeFile(tables.toString(), "router/src/main/resources/router_schema.sql");
    }
}
