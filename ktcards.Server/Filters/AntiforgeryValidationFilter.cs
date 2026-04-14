using Microsoft.AspNetCore.Antiforgery;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Filters;

namespace ktcards.Server.Filters
{
    public class AntiforgeryValidationFilter(IAntiforgery antiforgery) : IAsyncActionFilter
    {
        public async Task OnActionExecutionAsync(ActionExecutingContext context, ActionExecutionDelegate next)
        {
            var method = context.HttpContext.Request.Method;
            if (!HttpMethods.IsGet(method) && !HttpMethods.IsHead(method) &&
                !HttpMethods.IsOptions(method) && !HttpMethods.IsTrace(method))
            {
                try
                {
                    await antiforgery.ValidateRequestAsync(context.HttpContext);
                }
                catch (AntiforgeryValidationException)
                {
                    context.Result = new BadRequestObjectResult("CSRF token validation failed.");
                    return;
                }
            }

            await next();
        }
    }
}
