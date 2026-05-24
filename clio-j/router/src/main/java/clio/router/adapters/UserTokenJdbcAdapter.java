package clio.router.adapters;

import clio.core.db.JdbcAdapter;
import clio.router.TokenStore;

import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

public class UserTokenJdbcAdapter extends JdbcAdapter<TokenStore.UserToken> {

    public UserTokenJdbcAdapter() {
        super(TokenStore.UserToken.class);
    }

    @Override
    public void insert(TokenStore.UserToken obj, PreparedStatement stmt) throws SQLException {
        var i = 0;
        stmt.setTimestamp(++i, toTimestamp(obj.dttm()));
        stmt.setString(++i, obj.token());
        stmt.setString(++i, obj.username());
        stmt.setString(++i, obj.email());
    }

    @Override
    public TokenStore.UserToken select(ResultSet result) throws SQLException {
        var i = 0;
        var dttm = fromTimestamp(result.getTimestamp(++i));
        var token = result.getString(++i);
        var username = result.getString(++i);
        var email = result.getString(++i);
        return new TokenStore.UserToken(dttm, token, username, email);
    }
}
