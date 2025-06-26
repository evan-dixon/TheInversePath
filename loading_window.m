#import <Cocoa/Cocoa.h>

@interface LoadingWindowController : NSWindowController
@property (strong) NSProgressIndicator *progressIndicator;
@property (strong) NSTextField *loadingLabel;
@end

@implementation LoadingWindowController

- (id)init {
    if (self = [super initWithWindow:nil]) {
        NSRect screenRect = [[NSScreen mainScreen] frame];
        NSRect windowRect = NSMakeRect(0, 0, 300, 100);
        windowRect.origin.x = (screenRect.size.width - windowRect.size.width) / 2;
        windowRect.origin.y = (screenRect.size.height - windowRect.size.height) / 2;
        
        NSWindow *window = [[NSWindow alloc]
            initWithContentRect:windowRect
            styleMask:NSWindowStyleMaskTitled
            backing:NSBackingStoreBuffered
            defer:NO];
        [window setTitle:@"Loading"];
        [window setLevel:NSFloatingWindowLevel];
        [self setWindow:window];
        
        // Add progress indicator
        _progressIndicator = [[NSProgressIndicator alloc] initWithFrame:
            NSMakeRect(20, 50, 260, 20)];
        [_progressIndicator setStyle:NSProgressIndicatorStyleBar];
        [_progressIndicator setIndeterminate:YES];
        [_progressIndicator startAnimation:nil];
        [[window contentView] addSubview:_progressIndicator];
        
        // Add loading text
        _loadingLabel = [[NSTextField alloc] initWithFrame:
            NSMakeRect(20, 20, 260, 20)];
        [_loadingLabel setStringValue:@"Loading The Inverse Path..."];
        [_loadingLabel setAlignment:NSTextAlignmentCenter];
        [_loadingLabel setBezeled:NO];
        [_loadingLabel setDrawsBackground:NO];
        [_loadingLabel setEditable:NO];
        [_loadingLabel setSelectable:NO];
        [[window contentView] addSubview:_loadingLabel];
    }
    return self;
}

@end

int main(int argc, const char * argv[]) {
    @autoreleasepool {
        NSApplication *app = [NSApplication sharedApplication];
        LoadingWindowController *controller = [[LoadingWindowController alloc] init];
        [controller showWindow:nil];
        [app run];
    }
    return 0;
} 