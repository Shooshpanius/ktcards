var builder = WebApplication.CreateBuilder(args);

// Force the server to bind only to HTTP (disable HTTPS endpoints)
// UseUrls will override the default URLs and prevent HTTPS endpoints from being started.
builder.WebHost.UseUrls("http://localhost:5069");

// Add services to the container.

builder.Services.AddControllers();
// Learn more about configuring OpenAPI at https://aka.ms/aspnet/openapi
builder.Services.AddOpenApi();

var app = builder.Build();

app.UseDefaultFiles();
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
