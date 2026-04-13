using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Filters;
using ktcards.Server.Helpers;

namespace ktcards.Server.Filters
{
    [AttributeUsage(AttributeTargets.Method | AttributeTargets.Class)]
    public class AdminAuthorizeAttribute : Attribute, IActionFilter
    {
        private const string CookieName = "admin_session";

        public void OnActionExecuting(ActionExecutingContext context)
        {
            var tokenService = context.HttpContext.RequestServices.GetRequiredService<AdminTokenService>();
            var token = context.HttpContext.Request.Cookies[CookieName] ?? string.Empty;
            if (!tokenService.Validate(token))
            {
                context.Result = new UnauthorizedResult();
            }
        }

        public void OnActionExecuted(ActionExecutedContext context) { }
    }
}
