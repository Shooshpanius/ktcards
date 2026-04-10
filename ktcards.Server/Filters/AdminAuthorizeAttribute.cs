using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Filters;
using ktcards.Server.Helpers;

namespace ktcards.Server.Filters
{
    [AttributeUsage(AttributeTargets.Method | AttributeTargets.Class)]
    public class AdminAuthorizeAttribute : Attribute, IActionFilter
    {
        public void OnActionExecuting(ActionExecutingContext context)
        {
            var tokenService = context.HttpContext.RequestServices.GetRequiredService<AdminTokenService>();
            var authHeader = context.HttpContext.Request.Headers.Authorization.ToString();
            const string prefix = "Bearer ";
            if (!authHeader.StartsWith(prefix, StringComparison.OrdinalIgnoreCase) ||
                authHeader.Length <= prefix.Length ||
                !tokenService.Validate(authHeader[prefix.Length..]))
            {
                context.Result = new UnauthorizedResult();
            }
        }

        public void OnActionExecuted(ActionExecutedContext context) { }
    }
}
