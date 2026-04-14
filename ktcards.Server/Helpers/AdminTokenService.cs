using System.Security.Cryptography;

namespace ktcards.Server.Helpers
{
    public class AdminTokenService
    {
        private static readonly TimeSpan TokenLifetime = TimeSpan.FromHours(24);

        // token → creation time
        private readonly System.Collections.Concurrent.ConcurrentDictionary<string, DateTimeOffset> _tokens = new();

        public string CreateToken()
        {
            var token = Convert.ToHexString(RandomNumberGenerator.GetBytes(32));
            _tokens[token] = DateTimeOffset.UtcNow;
            PurgeExpired();
            return token;
        }

        public bool Validate(string token)
        {
            if (string.IsNullOrEmpty(token))
                return false;
            if (_tokens.TryGetValue(token, out var created))
                return DateTimeOffset.UtcNow - created < TokenLifetime;
            return false;
        }

        public void RevokeToken(string token)
        {
            _tokens.TryRemove(token, out _);
        }

        private void PurgeExpired()
        {
            var cutoff = DateTimeOffset.UtcNow - TokenLifetime;
            foreach (var key in _tokens.Keys)
            {
                if (_tokens.TryGetValue(key, out var created) && created < cutoff)
                    _tokens.TryRemove(key, out _);
            }
        }
    }
}
