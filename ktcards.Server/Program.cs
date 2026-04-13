using Microsoft.EntityFrameworkCore;
using System.Threading.RateLimiting;
using ktcards.Server.Data;
using ktcards.Server.Helpers;

var builder = WebApplication.CreateBuilder(args);

// Validate required configuration
var adminPassword = builder.Configuration["AdminPassword"] ?? string.Empty;
if (adminPassword.Length == 0)
    throw new InvalidOperationException(
        "AdminPassword is not configured. Set it via the AdminPassword environment variable.");

// Add services to the container.
var connectionString = builder.Configuration.GetConnectionString("Default")
    ?? throw new InvalidOperationException("Connection string 'Default' not found.");
builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseMySql(connectionString, new MariaDbServerVersion(new Version(10, 11, 0))));

builder.Services.AddControllers();
builder.Services.AddHttpClient();
builder.Services.AddSingleton<AdminTokenService>();

// Rate limiting: max 10 login attempts per minute per IP
builder.Services.AddRateLimiter(options =>
{
    options.AddPolicy("login", httpContext =>
        RateLimitPartition.GetFixedWindowLimiter(
            httpContext.Connection.RemoteIpAddress?.ToString() ?? "unknown",
            _ => new FixedWindowRateLimiterOptions
            {
                PermitLimit = 10,
                Window = TimeSpan.FromMinutes(1),
                QueueProcessingOrder = QueueProcessingOrder.OldestFirst,
                QueueLimit = 0
            }
        )
    );
    options.RejectionStatusCode = StatusCodes.Status429TooManyRequests;
});

// Learn more about configuring OpenAPI at https://aka.ms/aspnet/openapi
builder.Services.AddOpenApi();

var app = builder.Build();

// Auto-migrate / create database on startup
using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    db.Database.Migrate();
}

app.UseDefaultFiles();
app.UseStaticFiles();
app.MapStaticAssets();

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
}

app.UseRateLimiter();
app.UseAuthorization();

app.MapControllers();

app.MapFallbackToFile("/index.html");

app.Run();
