using System;
using Avalonia_UI.Api;

namespace Avalonia_UI.ViewModels;

public sealed class SharedPublicationShareOptionViewModel
{
    public SharedPublicationShareOptionViewModel(
        SharedPublicationCatalogEntryDto entry)
    {
        ShareName = entry.ShareName;
        LatestPublishedVersion = entry.LatestPublishedVersion;
        PublishedVersionCount = entry.PublishedVersionCount;
        LatestMemberCount = entry.LatestMemberCount;
        LatestCreatedAt = entry.LatestCreatedAt;
    }

    public string ShareName { get; }

    public int LatestPublishedVersion { get; }

    public int PublishedVersionCount { get; }

    public int LatestMemberCount { get; }

    public DateTimeOffset LatestCreatedAt { get; }

    public string DisplayText =>
        $"{ShareName} / v{LatestPublishedVersion} / {LatestMemberCount}";
}
