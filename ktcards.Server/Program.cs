using Microsoft.AspNetCore.HttpOverrides;
using Microsoft.AspNetCore.RateLimiting;
using Microsoft.EntityFrameworkCore;
using ktcards.Server.Data;
using ktcards.Server.Helpers;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
var connectionString = builder.Configuration.GetConnectionString("Default")
    ?? throw new InvalidOperationException("Connection string 'Default' not found.");
builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseMySql(connectionString, new MariaDbServerVersion(new Version(10, 11, 0))));

builder.Services.AddControllers();
builder.Services.AddHttpClient();
builder.Services.AddSingleton<AdminTokenService>();
// Learn more about configuring OpenAPI at https://aka.ms/aspnet/openapi
builder.Services.AddOpenApi();

builder.Services.Configure<ForwardedHeadersOptions>(options =>
{
    options.ForwardedHeaders = ForwardedHeaders.XForwardedFor | ForwardedHeaders.XForwardedProto;
    // Trust only the Docker private network range (172.16.0.0/12).
    // This prevents X-Forwarded-For spoofing from external clients while still allowing
    // the nginx container (front_ktcards) to forward the real client IP.
    // To further restrict to the exact Docker Compose subnet, run:
    //   docker network inspect <project>_default
    // and replace the network below with the actual "Subnet" value.
    options.KnownIPNetworks.Add(new System.Net.IPNetwork(
        System.Net.IPAddress.Parse("172.16.0.0"), 12));
});

builder.Services.AddRateLimiter(options =>
{
    options.AddFixedWindowLimiter("login", limiterOptions =>
    {
        limiterOptions.Window = TimeSpan.FromMinutes(1);
        limiterOptions.PermitLimit = 30;
        limiterOptions.QueueLimit = 0;
    });
    options.RejectionStatusCode = StatusCodes.Status429TooManyRequests;
});

var app = builder.Build();

// Validate required configuration
var adminPassword = app.Configuration["AdminPassword"];
if (string.IsNullOrEmpty(adminPassword))
    throw new InvalidOperationException(
        "AdminPassword is not configured. Set the AdminPassword configuration value or KTCARDS_ADMIN_PASSWORD environment variable before starting the application.");

// Auto-migrate / create database on startup
using (var scope = app.Services.CreateScope())
{
    var logger = scope.ServiceProvider.GetRequiredService<ILogger<Program>>();
    var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    try
    {
        db.Database.Migrate();
    }
    catch (Exception ex) when (ex is not OutOfMemoryException)
    {
        logger.LogCritical(ex, "Database migration failed. The application will shut down.");
        throw;
    }
}

app.UseForwardedHeaders();
app.UseRateLimiter();

app.UseDefaultFiles();
app.UseStaticFiles();
app.MapStaticAssets();

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
}

app.UseAuthorization();

app.MapControllers();

app.MapFallbackToFile("/index.html");

app.Run();
