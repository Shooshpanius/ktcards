namespace ktcards.Server.Helpers
{
    public class AdminTokenService
    {
        private readonly HashSet<string> _tokens = [];

        public string CreateToken()
        {
            var token = Guid.NewGuid().ToString("N");
            _tokens.Add(token);
            return token;
        }

        public bool Validate(string token) => !string.IsNullOrEmpty(token) && _tokens.Contains(token);
    }
}
