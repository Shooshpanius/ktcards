using Microsoft.EntityFrameworkCore;
using MySqlConnector;
using ktcards.Server.Data;
using ktcards.Server.Helpers;

var builder = WebApplication.CreateBuilder(args);

// Force the server to bind only to HTTP (disable HTTPS endpoints)
// UseUrls will override the default URLs and prevent HTTPS endpoints from being started.
builder.WebHost.UseUrls("http://localhost:5069");

// Add services to the container.
var connectionString = builder.Configuration.GetConnectionString("Default")
    ?? throw new InvalidOperationException("Connection string 'Default' not found.");
builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseMySql(connectionString, new MariaDbServerVersion(new Version(10, 11, 0))));

builder.Services.AddControllers();
builder.Services.AddSingleton<AdminTokenService>();
// Learn more about configuring OpenAPI at https://aka.ms/aspnet/openapi
builder.Services.AddOpenApi();

var app = builder.Build();

// Auto-migrate / create database on startup
const int MySqlErrorTableAlreadyExists = 1050;
using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    try
    {
        db.Database.Migrate();
    }
    catch (MySqlException ex) when (ex.Number == MySqlErrorTableAlreadyExists)
    {
        // Tables already exist but the EF migrations history table is missing
        // (pre-migration schema). Drop and recreate so migrations apply cleanly.
        db.Database.EnsureDeleted();
        db.Database.Migrate();
    }
}

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
