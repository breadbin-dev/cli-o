package clio.core;
public class LdapAllowAll extends Ldap {

    public LdapAllowAll() {
        super("ldap://dummy-url", "dummyUser", "dummyPwd", "dummySearch");
    }

    @Override
    public LdapUser lookupUser(String username) {
        return new LdapUser(username, "dn=allowAll", username + "@allowall.com");
    }

    @Override
    public boolean authUser(LdapUser user, String pwd) {
        return true;
    }

    @Override
    public LdapUser lookupAuthUser(String username, String password) {
        return lookupUser(username);
    }
}